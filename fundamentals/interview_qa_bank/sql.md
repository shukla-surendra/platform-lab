# SQL Questions and Answers

**Q1: What is the difference between CHAR and VARCHAR2?**

A: CHAR stores fixed-length character data and pads unused space with trailing spaces, while VARCHAR2 stores variable-length character data and does not pad unused space, saving storage.

**Q2: What is a view in SQL?**

A: A view functions as a virtual table created from a SELECT query that displays data from one or more tables without storing it, helping simplify queries and improve security.

**Q3: What is the purpose of the UNIQUE constraint?**

A: The constraint ensures that all values in a column (or combination of columns) are distinct, preventing duplicates and maintaining data integrity.

**Q4: What is a query in SQL?**

A: A query represents a SQL statement used to retrieve, update or manipulate data in a database, with SELECT statements being the most common type.

**Q5: What is a subquery?**

A: A subquery operates as a query nested within another query, often used in WHERE clauses to filter data based on another query's results for handling complex conditions.

**Q6: What is a composite primary key?**

A: It uses two or more columns together to uniquely identify each row when one column alone isn't sufficient.

**Q7: Explain the difference between the WHERE and HAVING clauses**

A: WHERE filters individual rows before grouping or aggregation, so it can't use aggregate functions like SUM or COUNT, while HAVING filters the resulting groups after GROUP BY.

**Q8: What are SQL joins and what are the differences between INNER, LEFT, RIGHT and FULL joins?**

A: SQL joins combine rows from two tables based on a matching condition. An INNER JOIN returns only matches that exist in both tables. A LEFT JOIN returns all rows from the left table and the matching rows from the right; when there's no match, right-side columns are NULL. A RIGHT JOIN is the mirror image: all rows from the right table plus matches from the left, NULL when absent. A FULL (OUTER) JOIN returns all rows from either table, filling in NULL where a counterpart is missing.

**Q9: Describe a PRIMARY KEY and how it differs from a UNIQUE key**

A: A PRIMARY KEY uniquely identifies each row in a table: it combines UNIQUE + NOT NULL, there can be only one per table (though it can be composite across multiple columns) and it's the default target for foreign keys. A UNIQUE key also enforces uniqueness, but doesn't require NOT NULL and you can have many UNIQUE constraints per table.

**Q10: What is a CTE (Common Table Expression) and when would you use it?**

A: A CTE represents a temporary named result set created using the WITH clause that exists only during the execution of a single SQL statement, used to simplify complex queries, improve readability, avoid repeating subqueries and write recursive queries.

**Q11: Explain normalization and briefly describe the different normal forms**

A: Normalization organizes relational data to minimize redundancy and prevent update/insert/delete anomalies by splitting tables based on dependencies. 1NF: each column contains atomic values, no repeating groups. 2NF: meets 1NF and removes partial dependencies on a composite primary key. 3NF: meets 2NF and removes transitive dependencies. BCNF: every determinant must be a candidate key. 4NF: removes multi-valued dependencies. 5NF (PJNF): removes join dependencies to avoid data redundancy.

**Q12: What is the difference between UNION and UNION ALL?**

A: UNION combines results from multiple SELECT queries and removes duplicate rows, while UNION ALL combines results from multiple SELECT queries and keeps all duplicate rows.

**Q13: How do clustered and non-clustered indexes differ?**

A: A clustered index stores table rows in the physical order of the index key, with only one allowed per table, best for range queries and sorting. A non-clustered index stores index data separately from the table with pointers to rows, allowing multiple per table, best for filtering, joins and fast lookups.

**Q14: How do you perform pattern matching in SQL?**

A: Pattern matching uses the LIKE operator with wildcard characters, where % matches zero or more characters and _ matches exactly one character.

**Q15: How would you calculate the running total of sales for each product?**

A: Use the SUM() window function with the OVER() clause, which adds each row's value to the cumulative total while keeping individual rows.

**Q16: Explain correlated subqueries and provide an example use case**

A: A correlated subquery represents a subquery that references columns from the outer query, executed once for each row processed by the outer query. Example: finding employees whose salary exceeds their department's average.

**Q17: What are EXISTS and NOT EXISTS and how do they differ from IN?**

A: EXISTS returns TRUE if the subquery returns at least one row. NOT EXISTS returns TRUE if the subquery returns no rows. IN checks whether a value exists in a list or the result of a subquery. Notably, EXISTS and NOT EXISTS stop searching as soon as a matching row is found.

**Q18: Explain anti-joins.**

A: An anti-join returns rows from one table that do not have matching rows in another table, commonly implemented using NOT EXISTS or a LEFT JOIN with IS NULL.

**Q19: Explain the difference between RANK(), DENSE_RANK() and ROW_NUMBER()**

A: ROW_NUMBER() assigns a unique number to each row with no gaps in numbering. RANK() assigns the same rank to duplicate values and skips the next rank after duplicates. DENSE_RANK() assigns the same rank to duplicate values but does not skip the next rank after duplicates.

**Q20: Explain the purpose of LAG and LEAD functions**

A: These are window functions used to access values from the previous or next row without using a self-join. LAG() returns the value from the previous row, while LEAD() returns the value from the next row, commonly used to compare consecutive rows, calculate differences and analyze trends.

**Q21: What is the difference between CROSS JOIN and INNER JOIN?**

A: CROSS JOIN returns the Cartesian product of both tables without requiring a join condition, while INNER JOIN returns only the matching rows based on a join condition requiring an ON clause.

**Q22: Explain foreign keys and how they enforce referential integrity**

A: A foreign key represents a column (or set of columns) in one table that references the primary key of another table, enforcing referential integrity by ensuring values in the child table exist in the parent table.

**Q23: Describe set operations like UNION, INTERSECT and EXCEPT and when each is useful**

A: UNION combines result sets and removes duplicate rows for merging data while keeping unique records. INTERSECT returns only the rows common to both result sets for finding records existing in both tables. EXCEPT (MINUS in Oracle) returns rows from the first query that are not in the second, for finding records present in one but missing in another.

**Q24: How would you optimize a slow query?**

A: Use EXPLAIN to find slow parts, add proper indexes and update statistics, use efficient conditions (avoid functions on columns), filter data early and avoid SELECT *, optimize joins and reduce extra data, rewrite queries if needed (JOIN, UNION ALL), and use pagination, caching or partitioning for large data.

**Q25: Explain database partitioning.**

A: Database partitioning represents the process of dividing a large table into smaller, manageable partitions while treating it as a single logical table, improving query performance, simplifying maintenance and enhancing scalability through horizontal or vertical approaches.

**Q26: What strategies can protect a web application from SQL injection?**

A: Use parameterized queries (prepared statements), validate and sanitize user input, avoid dynamic SQL created through string concatenation, use least-privilege database accounts, and use stored procedures securely.

**Q27: What are the main types of SQL commands?**

A: DDL (Data Definition Language): CREATE, ALTER, DROP, TRUNCATE. DML (Data Manipulation Language): SELECT, INSERT, UPDATE, DELETE. DCL (Data Control Language): GRANT, REVOKE. TCL (Transaction Control Language): COMMIT, ROLLBACK, SAVEPOINT.

**Q28: What is the purpose of the DEFAULT constraint?**

A: The constraint assigns a default value to a column when no value is provided during an INSERT operation, helping maintain consistent data and simplifying data entry.

**Q29: What is denormalization and when is it used?**

A: Denormalization represents the process of combining normalized tables into larger tables for performance reasons, used when complex queries and joins slow down data retrieval and performance benefits outweigh redundancy drawbacks.

**Q30: What are the different operators available in SQL?**

A: Arithmetic operators: +, -, *, /, %. Comparison operators: =, !=, <>, >, <, >=, <=. Logical operators: AND, OR, NOT. Set operators: UNION, INTERSECT, EXCEPT. Special operators: BETWEEN, IN, LIKE, IS NULL. Concatenation operators: || (Oracle, PostgreSQL) or + (SQL Server).

**Q31: What is a SELF JOIN and when is it used?**

A: A SELF JOIN represents a join in which a table is joined with itself, useful when rows within the same table have a relationship, such as employees and their managers or products with parent products.

**Q32: What is the purpose of the GROUP BY clause?**

A: The clause is used to arrange identical data into groups, typically used with aggregate functions (such as COUNT, SUM, AVG) to perform calculations on each group.

**Q33: What are aggregate functions in SQL?**

A: Aggregate functions perform calculations on a set of values and return a single value. Common functions: COUNT() returns the number of rows, SUM() returns the total sum of values, AVG() returns the average of values, MIN() returns the smallest value, MAX() returns the largest value.

**Q34: What are indexes and why are they used?**

A: Indexes represent database objects that improve query performance by allowing faster retrieval of rows, functioning like a book's index, making it quicker to find specific data without scanning the entire table, though they require additional storage and can slightly slow down modifications.

**Q35: What is the difference between DELETE and TRUNCATE commands?**

A: DELETE removes rows one by one, logs each deletion, allows rollback and supports WHERE clause, functioning as a DML command. TRUNCATE removes all rows at once, minimal logging, faster, no rollback and no WHERE clause, functioning as a DDL command.

**Q36: What are the differences between SQL and NoSQL databases?**

A: SQL databases use structured tables with rows and columns, follow a fixed schema, support ACID properties for reliable transactions, and are best for structured and stable data, scaling vertically. NoSQL databases use flexible, schema-less structures like key-value or documents, don't require a fixed schema, often prioritize performance and scalability over strict consistency, and scale horizontally.

**Q37: What are the types of constraints in SQL?**

A: NOT NULL ensures a column cannot have NULL values. UNIQUE ensures all values in a column are distinct. PRIMARY KEY uniquely identifies each row in a table. FOREIGN KEY ensures referential integrity by linking to a primary key in another table. CHECK ensures that all values in a column satisfy a specific condition. DEFAULT sets a default value for a column when no value is specified.

**Q38: What is a cursor in SQL?**

A: A cursor represents a database object used to retrieve, manipulate and traverse through rows in a result set one row at a time, helpful when performing operations that must be processed sequentially. Types include STATIC (snapshot of result set), DYNAMIC (reflects all changes), FORWARD_ONLY (only move forward), and KEYSET (uses a key to fetch rows).

**Q39: What is a trigger in SQL?**

A: A trigger represents a set of SQL statements that automatically execute in response to certain events on a table, such as INSERT, UPDATE or DELETE, helping maintain data consistency, enforce business rules and implement complex integrity constraints.

**Q40: What is the purpose of the SQL SELECT statement?**

A: The SELECT statement retrieves data from one or more tables, functioning as the most commonly used command in SQL, allowing users to filter, sort and display data based on specific criteria.

**Q41: What is the purpose of the ORDER BY clause?**

A: ORDER BY sorts the result set of a query in ascending or descending order based on one or more columns.

**Q42: What is a table in SQL?**

A: A table represents a structured collection of related data organized into rows and columns, where columns define the type of data stored, while rows contain individual records.

**Q43: What are NULL values in SQL?**

A: NULL represents a missing or unknown value, different from zero or an empty string, indicating that the data is not available or applicable.

**Q44: What is a stored procedure?**

A: A stored procedure represents a precompiled set of SQL statements stored in the database, able to take input parameters, perform logic and queries and return output values or result sets, improving performance and maintainability by centralizing business logic.

**Q45: What is the difference between DDL and DML commands?**

A: DDL (Data Definition Language) is used to define and modify the structure of the database on tables, schemas and database objects, including commands like CREATE, ALTER and DROP. DML (Data Manipulation Language) is used to manage and manipulate the data inside the database on rows stored in tables, including commands like INSERT, UPDATE and DELETE.

**Q46: What is the purpose of the ALTER command in SQL?**

A: The ALTER command is used to modify the structure of an existing database object, enabling capabilities to add or drop a column in a table, change a column's data type, add or remove constraints, rename columns or tables, and adjust indexing or storage settings.

**Q47: How is data integrity maintained in SQL databases?**

A: Through constraints (ensuring conditions are always met), transactions (ensuring a series of operations either all succeed or all fail), triggers (automatically enforcing rules before/after changes), normalization (organizing data into related tables to minimize redundancy), and cascading actions (foreign keys with ON DELETE CASCADE / ON UPDATE CASCADE).

**Q48: How does the CASE statement work in SQL?**

A: The CASE statement is SQL's way of implementing conditional logic in queries, evaluating conditions and returning a value based on the first condition that evaluates to true, returning a default value using the ELSE clause if no condition is met.

**Q49: What is the purpose of the COALESCE function?**

A: The COALESCE function returns the first non-NULL value from a list of expressions, commonly used to provide default values or handle missing data gracefully.

**Q50: What are the differences between SQL's COUNT() and SUM() functions?**

A: COUNT() counts number of rows or non-NULL values, while SUM() adds all numeric values in a column.

**Q51: What is the difference between the NVL and NVL2 functions?**

A: NVL() replaces NULL with a given value, taking 2 arguments. NVL2() returns one value if NOT NULL, another if NULL, taking 3 arguments.

**Q52: What are scalar functions in SQL?**

A: Scalar functions operate on individual values and return a single value as a result, often used for formatting or converting data, with common examples including LEN() (returns the length of a string), ROUND() (rounds a numeric value), and CONVERT() (converts a value from one data type to another).

**Q53: What happens if you use COUNT() on NULLs?**

A: COUNT(column) ignores NULL values and only counts non-NULL entries, while COUNT(*) counts all rows, including those with NULL values in columns.

**Q54: What are window functions and how are they used?**

A: Window functions perform calculations across a group of related rows while keeping each row separate, used for tasks like running totals, rankings and moving averages.

**Q55: What is the difference between an index and a key in SQL?**

A: An index is used to improve data retrieval speed, represents a physical database object, and does not ensure uniqueness (can be non-unique). A key is used to enforce data integrity and relationships, represents a logical concept, and ensures uniqueness (e.g., Primary Key).

**Q56: How does indexing improve query performance?**

A: Indexing helps the database quickly find data without scanning the whole table, reducing time and improving query performance.

**Q57: What are the trade-offs of using indexes in SQL databases?**

A: Advantages include faster query performance, especially for SELECT queries with WHERE clauses, JOIN conditions or ORDER BY clauses, and improved sorting and filtering efficiency. Disadvantages include increased storage space for the index structures and additional overhead for write operations (INSERT, UPDATE, DELETE).

**Q58: What are temporary tables and how are they used?**

A: Temporary tables represent tables that exist only for the duration of a session or a transaction, useful for storing intermediate results, simplifying complex queries, or performing operations on subsets of data.

**Q59: What is a materialized view and how does it differ from a standard view?**

A: A standard view functions as a virtual table defined by a query that does not store data; the underlying query is executed each time the view is referenced. A materialized view represents a physical table that stores the result of the query where data is precomputed and stored, making reads faster but requires periodic refreshes to keep data up to date.

**Q60: What is a sequence in SQL?**

A: A sequence represents a database object that generates a series of unique numeric values, often used to produce unique identifiers for primary keys or other columns requiring sequential values.

**Q61: What is the purpose of the SQL EXCEPT operator?**

A: The EXCEPT operator is used to return rows from one query's result set that are not present in another query's result set, effectively performing a set difference, showing only the data that is unique to the first query.

**Q62: How do constraints improve database integrity?**

A: Constraints enforce rules that the data must follow, preventing invalid or inconsistent data from being entered, with examples including NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY, and CHECK constraints.

**Q63: What is the difference between a local and a global temporary table?**

A: A local temporary table is prefixed with # (e.g., #TempTable), exists only within the session that created it, and automatically drops when the session ends. A global temporary table is prefixed with ## (e.g., ##GlobalTempTable), remains visible to all sessions, and drops only when all sessions referencing it are closed.

**Q64: What is the purpose of the SQL MERGE statement?**

A: The MERGE statement combines multiple operations INSERT, UPDATE and DELETE into one, used to synchronize two tables by inserting rows that don't exist, updating rows that already exist, and deleting rows based on conditions.

**Q65: How can you handle duplicates in a query without using DISTINCT?**

A: Use GROUP BY (aggregate rows to eliminate duplicates) or ROW_NUMBER() (assign a unique number to each row and filter by that).

**Q66: What are the ACID properties of a transaction?**

A: Atomicity: a transaction is completed entirely or not at all. Consistency: ensures the database remains valid by following all rules and constraints. Isolation: multiple transactions execute independently without affecting each other. Durability: once a transaction is committed, its changes are permanently saved.

**Q67: What are the differences between isolation levels in SQL?**

A: Read Uncommitted allows reading uncommitted data, which may cause dirty reads. Read Committed reads only committed data, preventing dirty reads. Repeatable Read ensures the same data remains unchanged during a transaction. Serializable provides the highest isolation level, preventing dirty reads, non-repeatable reads, and phantom reads.

**Q68: What is the purpose of the WITH (NOLOCK) hint in SQL Server?**

A: The WITH (NOLOCK) hint allows a query to read data without acquiring shared locks, effectively reading uncommitted data, improving performance by reducing contention for locks, especially on large tables that are frequently updated, though results may be inconsistent or unreliable.

**Q69: How do you handle deadlocks in SQL databases?**

A: Deadlock detection & retry (the database detects the deadlock, aborts one transaction and retries it later), reduce lock contention (use indexes, optimize queries, keep transactions short), choose appropriate isolation levels, and consistent resource ordering (access resources in the same order across transactions).

**Q70: What is a database snapshot and how is it used?**

A: A database snapshot represents a read-only copy of a database at a specific point in time, useful for reporting on a consistent dataset, point-in-time recovery, and testing without affecting the original database.

**Q71: What are the differences between OLTP and OLAP systems?**

A: OLTP handles simple, frequent transactions, is optimized for fast read and write operations, and finds use in e-commerce, banking systems. OLAP handles complex queries and data analysis, is optimized for read-heavy workloads and aggregation, and finds use in data warehousing, business intelligence.

**Q72: What is a live lock and how does it differ from a deadlock?**

A: A live lock occurs when two or more transactions keep responding to each other's changes, but no progress is made, with transactions actively running but unable to complete. A deadlock occurs when two or more transactions are waiting on each other's resources indefinitely, blocking all progress.

**Q73: How do you implement dynamic SQL and what are its advantages and risks?**

A: Dynamic SQL is created and executed at runtime using variables or user input. Advantages: builds flexible queries dynamically, useful for dynamic filtering, sorting, and table selection. Risks: vulnerable to SQL injection if inputs are not validated, harder to debug and maintain, may reduce query performance.

**Q74: What is the difference between horizontal and vertical partitioning?**

A: Horizontal partitioning divides rows of a table based on column values, while vertical partitioning divides columns of a table into separate parts.

**Q75: What are the considerations for indexing very large tables?**

A: Index frequently used columns (WHERE, JOIN, ORDER BY clauses), choose the right index type (clustered for primary keys and range queries), use partitioned indexes (local indexes for partitioned tables), maintain indexes (rebuild fragmented indexes off-peak), and monitor performance (analyze execution plans, remove unused indexes).

**Q76: What is the difference between database sharding and partitioning?**

A: Sharding splits a database into multiple independent databases across servers for horizontal scaling, while partitioning splits a table into parts within the same database for better performance and data management.

**Q77: What are the best practices for writing optimized SQL queries?**

A: Write simple queries, filter data early with WHERE clauses, avoid SELECT * (retrieve only required columns), use indexes effectively, analyze execution plans, optimize joins & aggregations, and monitor and continuously tune performance.

**Q78: How can you monitor query performance in a production database?**

A: Use execution plans to identify bottlenecks, analyze wait statistics (locks, I/O, CPU), use monitoring tools (EXPLAIN, Query Store, Performance Schema), track performance metrics (query time, CPU, I/O), and continuously tune queries.

**Q79: What are the trade-offs of using indexing versus denormalization?**

A: Indexing improves query performance by speeding up data retrieval without duplicating data, but slows insert/update/delete operations and requires additional storage. Denormalization improves read performance by reducing joins, but introduces data redundancy, makes updates more complex, and requires additional storage.

**Q80: How does SQL handle recursive queries?**

A: SQL uses recursive CTEs to retrieve hierarchical or tree-structured data, employing a base query followed by a recursive member using UNION ALL to build the complete result set.

**Q81: What are the differences between transactional and analytical queries?**

A: Transactional queries focus on short, day-to-day operations like INSERT, UPDATE, DELETE, optimized for high speed and low latency, used in OLTP systems. Analytical queries focus on complex analysis, aggregations and transformations, process large volumes of data, used in OLAP systems for analysis and reporting.

**Q82: How can you ensure data consistency across distributed databases?**

A: Distributed transactions (ensure all databases commit or roll back together, e.g. 2PC), eventual consistency, conflict resolution (timestamps or versioning), data replication, and audits & validation.

**Q83: What is the purpose of the SQL PIVOT operator?**

A: The PIVOT operator transforms rows into columns, making it easier to summarize or rearrange data for reporting.

**Q84: What is a bitmap index and how does it differ from a B-tree index?**

A: A bitmap index uses bitmaps (arrays of bits) to represent data, is suitable for low-cardinality columns, and is best for filtering and boolean conditions. A B-tree index uses a balanced tree structure to store data in sorted order, is suitable for high-cardinality columns, and is best for searching and sorting large datasets.

**Q85: Difference between blocking and deadlocking.**

A: Blocking: one transaction waits because another holds the lock, resolves automatically after lock release. Deadlocking: two or more transactions wait for each other (circular wait), needs detection and rollback to resolve.

**Q86: Delete duplicate data from table only first data remains constant.**

A: Use a query joining the table to itself, matching on duplicate-identifying columns while keeping only the lowest ID values for deletion.

**Q87: Find the employee name using COALESCE() when First_Name, Second_Name, or Last_Name may contain NULL values.**

A: `SELECT ID, COALESCE(FName, SName, LName) as Name FROM employees;` returns the first non-NULL name field for each employee.

**Q88: Find employees hired in the last n months using the TIMESTAMPDIFF() function.**

A: `SELECT *, TIMESTAMPDIFF(month, Hiredate, current_date()) as DiffMonth FROM employees WHERE TIMESTAMPDIFF(month, Hiredate, current_date()) BETWEEN 1 AND 5 ORDER BY Hiredate DESC;` identifies recently hired employees.

**Q89: What is the difference between INNER JOIN and LEFT JOIN?**

A: INNER JOIN returns only the rows where there is a matching value in both the left and right tables, while LEFT JOIN returns every row from the left table regardless of a match; if no corresponding row exists in the right table, the result set will contain NULL values.

**Q90: Explain the difference between WHERE and HAVING.**

A: WHERE clause is used to filter individual rows of data before any groupings or aggregations are performed, while HAVING clause is specifically designed to filter the results of aggregate functions and must be used after a GROUP BY clause.

**Q91: What is a Self Join and when would you use it?**

A: A self join pairs a table with itself using different aliases. It's commonly used when a table has a recursive relationship, such as an employee table that contains a manager_id pointing back to the employee_id of another row.

**Q92: How do you find duplicate rows in a table?**

A: Select the columns to check, use GROUP BY on those columns, then apply a HAVING COUNT(*) > 1 filter to identify groups appearing more than once.

**Q93: What is the difference between UNION and UNION ALL?**

A: UNION performs a distinct operation on the combined result set, removing duplicate rows, while UNION ALL simply appends the result sets together without checking for duplicates.

**Q94: What is a CROSS JOIN?**

A: A CROSS JOIN creates a Cartesian product between two tables, meaning every single row from the first table is paired with every single row from the second table.

**Q95: How do you select the top N records from a table?**

A: Syntax varies by database: PostgreSQL, MySQL, and BigQuery use LIMIT N; SQL Server uses SELECT TOP N; Oracle typically uses FETCH FIRST N ROWS ONLY.

**Q96: What does the COALESCE function do?**

A: COALESCE evaluates a list of arguments in order and returns the first value that is not NULL.

**Q97: What is the purpose of the DISTINCT keyword?**

A: DISTINCT is used within a SELECT statement to remove duplicate rows from the output, ensuring each row is unique based on specified columns.

**Q98: How do you handle NULL values in a comparison?**

A: Standard comparison operators like = or != do not work with NULL; you must use IS NULL or IS NOT NULL to accurately filter for missing data.

**Q99: What are Aggregate Functions?**

A: Aggregate functions perform a calculation on a set of values across multiple rows to return a single, summary value, with examples including SUM, AVG, COUNT, MIN, MAX.

**Q100: Explain the difference between RANK(), DENSE_RANK(), and ROW_NUMBER().**

A: ROW_NUMBER assigns unique sequential integers; RANK assigns the same number to ties but skips subsequent numbers; DENSE_RANK assigns the same numbers to ties without skipping.

**Q101: What is a Common Table Expression (CTE)?**

A: A CTE is a temporary, named result set defined using WITH that exists only during execution of a single query, making complex queries easier to read.

**Q102: When would you use a Subquery vs. a CTE?**

A: CTEs are generally preferred for readability and modularity; subqueries are often used for simple, one-off filters where CTE overhead feels unnecessary.

**Q103: What is a Window Function?**

A: A window function performs a calculation across a set of rows related to the current row but doesn't collapse rows, allowing original data alongside calculations.

**Q104: How do you calculate a running total in SQL?**

A: Use the SUM() aggregate function as a window function by adding an OVER clause with an ORDER BY sub-clause, like `SUM(sales) OVER (ORDER BY date)`.

**Q105: What is the LEAD() and LAG() function?**

A: LAG() provides access to a value in a row behind the current row; LEAD() provides access to a value ahead of the current row, useful for period-over-period growth.

**Q106: Explain the CASE statement.**

A: CASE statement implements if-then-else logic, allowing evaluation of conditions to return specific values, essential for data cleaning and categorization.

**Q107: What is the difference between a Primary Key and a Unique Key?**

A: Primary Key uniquely identifies each record and prohibits NULL values (one per table); Unique Key ensures distinct values but allows NULLs and permits multiple per table.

**Q108: What is a Foreign Key?**

A: A Foreign Key is a column referencing the Primary Key of another table, enforcing referential integrity to prevent orphan records.

**Q109: What is an Index and how does it affect performance?**

A: Index is a data structure (typically B-Tree) enabling faster row finding; it dramatically speeds up reads but slows writes since updates must maintain the index.

**Q110: Explain the concept of Partitioning in SQL.**

A: Partitioning physically divides a large table into smaller segments based on a column like date or region, improving performance through partition pruning.

**Q111: What is the difference between a Clustered and Non-Clustered index?**

A: Clustered Index determines physical storage order (one per table); Non-Clustered Index is a separate object with data pointers (multiple per table allowed).

**Q112: What is a View?**

A: A View is a virtual table consisting of a stored SQL query that doesn't store data itself but provides simplified access or security restrictions.

**Q113: What is a Materialized View?**

A: Unlike standard views, a Materialized View physically stores query results on disk, offering performance gains but requiring refresh strategies for staleness management.

**Q114: How would you delete duplicate records while keeping only one?**

A: Use a CTE with ROW_NUMBER() partitioned by duplicate-defining columns; delete all rows where the row number is greater than 1.

**Q115: What are ACID properties?**

A: Atomicity (all or nothing), Consistency (valid transitions), Isolation (concurrent non-interference), Durability (persistence).

**Q116: Explain Normalization and its levels.**

A: Normalization reduces redundancy: 1NF requires atomic values; 2NF removes partial dependencies; 3NF removes transitive dependencies.

**Q117: What is Denormalization and why do Data Engineers do it?**

A: Denormalization intentionally introduces redundancy by combining tables to reduce joins needed for queries, improving read performance in analytical environments.

**Q118: What is a Star Schema?**

A: Star Schema connects a central Fact Table (quantitative metrics) to multiple Dimension Tables (descriptive attributes), optimized for OLAP systems.

**Q119: How do you optimize a slow-running query?**

A: Review the execution plan for bottlenecks like full table scans. Common fixes include adding indexes, updating statistics, avoiding SELECT *, and reducing wildcard usage.

**Q120: What is an Execution Plan?**

A: Execution plan is a report showing steps the database engine will take to fulfill a query, including index usage, join types, and operation costs.

**Q121: What is the N+1 Problem in database queries?**

A: This occurs when one query gets a list of IDs and then separate queries execute for each ID. Data engineers solve this using set-based logic with joins.

**Q122: How do you find the second-highest salary in an Employee table?**

A: Use `SELECT MAX(salary) FROM Employee WHERE salary < (SELECT MAX(salary) FROM Employee)` or sort by salary descending with OFFSET 1 LIMIT 1.

**Q123: How do you handle SCD Type 2 (Slowly Changing Dimensions) in SQL?**

A: Track historical changes by creating new rows; include valid_from and valid_to timestamps or an is_current flag for point-in-time lookups.

**Q124: Explain the difference between TRUNCATE and DELETE.**

A: DELETE is DML removing rows individually with logging and WHERE support; TRUNCATE is DDL deallocating data pages much faster but without WHERE filtering.

**Q125: What is a Stored Procedure?**

A: Stored Procedure is a group of compiled SQL statements stored on the database server allowing complex logic, improved security, and reduced network traffic.

**Q126: What is a Trigger?**

A: Trigger is a special stored procedure automatically executing in response to INSERT, UPDATE, or DELETE events, used for auditing and enforcing business rules.

**Q127: How do you handle Big Data in SQL (billions of rows)?**

A: Standard databases struggle; use distributed systems like Snowflake or BigQuery relying on columnar storage and massively parallel processing.

**Q128: What is the difference between OLTP and OLAP?**

A: OLTP optimizes frequent small writes and lookups; OLAP optimizes complex long-running aggregation queries over massive datasets.

**Q129: What is Upsert?**

A: Upsert attempts updating existing records by unique key but inserts new records if keys aren't found, typically using a MERGE statement.

**Q130: How do you convert a String to a Date in SQL?**

A: Methods vary: PostgreSQL uses TO_DATE(); SQL Server uses CONVERT(); modern warehouses like Snowflake allow casting to DATE.

**Q131: What is a Full Outer Join?**

A: Full Outer Join combines Left and Right Outer Joins, returning all records from both tables with NULLs where matches don't exist.

**Q132: What is Data Profiling?**

A: Data profiling uses SQL to explore datasets by calculating NULL percentages, value distributions, unique counts, and identifying data quality issues.

**Q133: How do you pivot data from rows to columns?**

A: Use a built-in PIVOT operator in some dialects, or combine aggregate functions with CASE statements like `SUM(CASE WHEN category='A' ...)`.

**Q134: Explain Sharding.**

A: Sharding splits data across independent database instances (shards), where each has an identical schema but a different data subset, for horizontal scaling.

**Q135: What is the difference between a Temporary Table and a Table Variable?**

A: Temporary Tables are physical objects with index support visible across sessions; Table Variables are memory-based with limited scope, better for small data.

**Q136: How do you use the EXPLAIN keyword?**

A: Place EXPLAIN before a SELECT statement; the database returns a query plan instead of data, for diagnosing performance issues.

**Q137: What is a Correlation Subquery?**

A: A correlated subquery depends on outer query values, re-evaluating for every row; extremely slow on large datasets and should often be rewritten as a join.

**Q138: Why is Sargability important?**

A: Sargability determines if a query can utilize an index; wrapping columns in functions breaks this, forcing full table scans instead of index seeks.
