# Unicode Handling Requirements

**Purpose**: Prevent encoding corruption when working with non-ASCII data (Greek, Chinese, Arabic, etc.) in Python + SQL Server.

> **Key Principle**: String comparison doesn't catch encoding bugs. Always verify with UNICODE() values.

---

## The Problem

When transferring text between Python and SQL Server:
- SQL Server NVARCHAR uses UTF-16 internally
- Python strings are UTF-8
- pyodbc encoding configuration is non-obvious
- String comparison (`sent == received`) can pass even when data is corrupted

**Example from Etymython**:
```
Original:     Ζεύς (Unicode 918 - correct Greek)
After save:   Î–ÎµÏÏ‚ (Unicode 206 - mojibake)
String test:  sent == received → Could still pass if both corrupted same way
```

---

## Encoding Bug Indicators

| Unicode Value | Meaning | Indicates |
|---------------|---------|-----------|
| 63 | `?` | Data completely lost (replacement character) |
| 206, 195, 194 | `Î`, `Ã`, `Â` | UTF-8 bytes misread as Latin-1 (mojibake) |
| 225, 226 | `á`, `â` | Similar mojibake pattern |
| 913-1023 | Greek letters | Correct basic Greek |
| 7936-8191 | Polytonic Greek | Correct extended Greek |

---

## Verification Method

### ❌ WRONG: String Comparison
```python
# This can pass even with corrupted data!
sent_string = "Ζεύς"
received_string = cursor.fetchone()[0]
assert sent_string == received_string  # May pass with mojibake
```

### ✅ CORRECT: Unicode Value Verification
```sql
-- SQL Server verification
SELECT 
    greek_column,
    UNICODE(LEFT(greek_column, 1)) as first_char_code,
    CASE 
        WHEN UNICODE(LEFT(greek_column, 1)) BETWEEN 913 AND 1023 THEN 'Valid Greek'
        WHEN UNICODE(LEFT(greek_column, 1)) BETWEEN 7936 AND 8191 THEN 'Valid Polytonic'
        WHEN UNICODE(LEFT(greek_column, 1)) = 63 THEN 'DATA LOST (?)'
        WHEN UNICODE(LEFT(greek_column, 1)) IN (206, 195, 194, 225) THEN 'MOJIBAKE'
        ELSE 'Unknown - investigate'
    END as status
FROM table_with_greek;
```

```python
# Python verification
def verify_greek_encoding(cursor, table, column):
    """Verify Greek text is correctly encoded using Unicode values"""
    cursor.execute(f"""
        SELECT {column}, UNICODE(LEFT({column}, 1)) as code
        FROM {table}
        WHERE {column} IS NOT NULL
    """)
    
    issues = []
    for row in cursor.fetchall():
        text, code = row
        if code == 63:
            issues.append(f"DATA LOST: {text}")
        elif code in (206, 195, 194, 225, 226):
            issues.append(f"MOJIBAKE (code {code}): {text}")
        elif not (913 <= code <= 1023 or 7936 <= code <= 8191):
            issues.append(f"UNEXPECTED (code {code}): {text}")
    
    return issues
```

---

## Correct pyodbc Configuration

### For SQL Server NVARCHAR Columns

```python
import pyodbc

# Connection setup
conn = pyodbc.connect(connection_string)

# CRITICAL: Set encoding for SQL Server Unicode columns
conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
conn.setdecoding(pyodbc.SQL_WMETADATA, encoding='utf-16-le')
conn.setencoding(encoding='utf-16-le')

# Now Unicode operations should work correctly
cursor = conn.cursor()
cursor.execute("INSERT INTO table (greek_col) VALUES (N'Ζεύς')")
```

### Complete Connection Pattern

```python
def get_unicode_safe_connection(connection_string):
    """Create a pyodbc connection configured for Unicode"""
    conn = pyodbc.connect(connection_string)
    
    # UTF-16LE for SQL Server NVARCHAR
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
    conn.setdecoding(pyodbc.SQL_WMETADATA, encoding='utf-16-le')
    conn.setencoding(encoding='utf-16-le')
    
    return conn
```

---

## Database Schema Requirements

### Column Types
```sql
-- Use NVARCHAR for any non-ASCII text
CREATE TABLE example (
    id INT PRIMARY KEY,
    english_name VARCHAR(100),      -- ASCII only
    greek_name NVARCHAR(100),       -- Unicode required
    description NVARCHAR(MAX)       -- Unicode required
);
```

### Inserting Unicode Data
```sql
-- Always use N prefix for Unicode literals
INSERT INTO example (greek_name) VALUES (N'Ζεύς');

-- Without N prefix, data may be corrupted
INSERT INTO example (greek_name) VALUES ('Ζεύς');  -- WRONG!
```

---

## Testing Sequence for Unicode Data

### 1. Unit Test (Single Record)
```python
def test_single_greek_record():
    """Test one record with known Greek text"""
    test_text = "Ζεύς"
    expected_unicode = 918  # Ζ = Greek capital Zeta
    
    # Insert
    cursor.execute("INSERT INTO test_table (greek_col) VALUES (?)", test_text)
    conn.commit()
    
    # Verify with UNICODE(), not string comparison
    cursor.execute("""
        SELECT greek_col, UNICODE(LEFT(greek_col, 1)) 
        FROM test_table 
        WHERE id = SCOPE_IDENTITY()
    """)
    result_text, result_code = cursor.fetchone()
    
    assert result_code == expected_unicode, f"Expected {expected_unicode}, got {result_code}"
    print(f"✓ Unicode verification passed: {result_text} (code {result_code})")
```

### 2. Small Batch Test (3-5 Records)
```python
def test_greek_batch():
    """Test several Greek texts"""
    test_cases = [
        ("Ζεύς", 918),      # Zeus
        ("Ἥρα", 7977),      # Hera (polytonic)
        ("Ἀθηνᾶ", 7944),    # Athena (polytonic)
    ]
    
    for text, expected_code in test_cases:
        # Insert and verify each
        cursor.execute("INSERT INTO test_table (greek_col) VALUES (?)", text)
        cursor.execute("""
            SELECT UNICODE(LEFT(greek_col, 1)) 
            FROM test_table 
            WHERE id = SCOPE_IDENTITY()
        """)
        actual_code = cursor.fetchone()[0]
        
        assert actual_code == expected_code, f"{text}: expected {expected_code}, got {actual_code}"
    
    print(f"✓ Batch test passed: {len(test_cases)} records")
```

### 3. Golden Audit for Production Data
```sql
-- Add to Golden Audit stored procedure
SELECT 
    'ENCODING_CHECK' as audit_type,
    COUNT(*) as total_records,
    SUM(CASE 
        WHEN UNICODE(LEFT(greek_column, 1)) BETWEEN 913 AND 1023 THEN 0
        WHEN UNICODE(LEFT(greek_column, 1)) BETWEEN 7936 AND 8191 THEN 0
        ELSE 1 
    END) as encoding_violations
FROM table_with_greek
WHERE greek_column IS NOT NULL;
```

---

## Recovery from Encoding Corruption

### Step 1: Identify Corruption Extent
```sql
SELECT 
    id,
    greek_column,
    UNICODE(LEFT(greek_column, 1)) as first_char,
    CASE 
        WHEN UNICODE(LEFT(greek_column, 1)) = 63 THEN 'LOST'
        WHEN UNICODE(LEFT(greek_column, 1)) IN (206, 195, 194) THEN 'MOJIBAKE'
        ELSE 'CHECK'
    END as status
FROM table_with_greek
WHERE UNICODE(LEFT(greek_column, 1)) NOT BETWEEN 913 AND 1023
  AND UNICODE(LEFT(greek_column, 1)) NOT BETWEEN 7936 AND 8191;
```

### Step 2: Backup Before Recovery
```sql
SELECT * INTO table_backup_YYYYMMDD FROM table_with_greek;
```

### Step 3: Recovery Options

| Corruption Type | Recovery Option |
|-----------------|-----------------|
| `?` (code 63) | Data lost - restore from backup or re-enter |
| Mojibake | May be recoverable with encoding conversion |
| Mixed | Restore from backup recommended |

### Step 4: Verify Recovery
```sql
-- Run Golden Audit after recovery
EXEC usp_GoldenAudit;

-- Expect 0 encoding violations
```

---

## Checklist for Unicode Operations

Before any operation involving non-ASCII text:

```
[ ] pyodbc connection has UTF-16LE encoding set
[ ] Database columns are NVARCHAR (not VARCHAR)
[ ] SQL literals use N prefix (N'text')
[ ] Verification uses UNICODE() not string comparison
[ ] Single-record test passed with code verification
[ ] Small batch test passed
[ ] Golden Audit includes encoding check
[ ] Backup created before bulk operations
```

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Missing `conn.setencoding()` | Mojibake on write | Add UTF-16LE encoding setup |
| VARCHAR instead of NVARCHAR | Data truncated/corrupted | Use NVARCHAR for Unicode |
| Missing N prefix in SQL | Implicit conversion corruption | Always use N'text' |
| String comparison for verification | False positives | Use UNICODE() function |
| Bulk update without unit test | Widespread corruption | Test single record first |

---

**Template Version**: 3.9  
**Last Updated**: January 2026  
**Methodology**: [coreyprator/project-methodology](https://github.com/coreyprator/project-methodology)
