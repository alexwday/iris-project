-- Create tables for the Finance Document System

-- 1. apg_catalog Table
CREATE TABLE apg_catalog (
    -- SYSTEM fields
    id SERIAL PRIMARY KEY,                        -- Auto-incrementing unique identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- When the record was added to the database
    
    -- DOCUMENT identification fields
    document_source VARCHAR(100) NOT NULL,        -- Source of the document (e.g., 'internal_capm', 'external_iasb')
    document_type VARCHAR(100) NOT NULL,          -- Type of document (e.g., 'capm', 'infographic', 'memo')
    document_name VARCHAR(255) NOT NULL,          -- Formatted document name (e.g., 'IFRS 9 - Financial Instruments')
    
    -- SCOPE fields
    document_description TEXT,                    -- AI-generated description of document usage/scope
    
    -- REFRESH metadata fields
    date_created TIMESTAMP WITH TIME ZONE,        -- Original document creation date
    date_last_modified TIMESTAMP WITH TIME ZONE,  -- Date the document was last modified
    file_name VARCHAR(255),                       -- Full filename with extension (e.g., 'IFRS9_Financial_Instruments.pdf')
    file_type VARCHAR(50),                        -- File extension/type (e.g., '.pdf', '.docx', '.xlsx')
    file_size BIGINT,                             -- Size of the file in bytes
    file_path VARCHAR(1000)                       -- Full system path to the original file
);

-- 2. apg_content Table
CREATE TABLE apg_content (
    -- SYSTEM fields
    id SERIAL PRIMARY KEY,                        -- Auto-incrementing unique identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- When the record was added to the database
    
    -- DOCUMENT reference fields (matching catalog)
    document_source VARCHAR(100) NOT NULL,        -- Source of the document (matches apg_catalog)
    document_type VARCHAR(100) NOT NULL,          -- Type of document (matches apg_catalog)
    document_name VARCHAR(255) NOT NULL,          -- Document name (matches apg_catalog)
    
    -- CONTENT fields
    section_id INTEGER NOT NULL,                  -- Ordered sequence number within the document
    section_name VARCHAR(500),                    -- Title of the section/chapter
    section_summary TEXT,                         -- AI-generated summary of the section
    section_content TEXT NOT NULL                 -- The actual content of the section
);