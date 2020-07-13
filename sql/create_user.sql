USE Infinite_Challenge;
CREATE LOGIN db_user WITH PASSWORD = 'infinite';
CREATE USER db_user FOR LOGIN db_user WITH DEFAULT_SCHEMA = dbo;

Use Infinite_Challenge go
GRANT SELECT, INSERT, UPDATE ON SCHEMA :: dbo TO db_user;

Use master go
GRANT ADMINISTER BULK OPERATIONS TO db_user;