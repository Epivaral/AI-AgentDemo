-- Drop the table if it exists
IF OBJECT_ID('dbo.Tasks', 'U') IS NOT NULL
    DROP TABLE dbo.Tasks;

-- Create the Tasks table
CREATE TABLE dbo.Tasks (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    UserId NVARCHAR(50),
    TaskText NVARCHAR(255),
    Completed BIT DEFAULT 0
);
