#!/usr/bin/env python3
"""
IRIS Database Configuration Sync Tool

Unified script for syncing prompts and database registry between
PostgreSQL and local backup files.

Usage:
    # Download everything from PostgreSQL to backups folder
    python db_config/sync.py download

    # Upload everything from backups folder to PostgreSQL
    python db_config/sync.py upload

    # Download with archive (saves current backups before overwriting)
    python db_config/sync.py download --archive

    # Upload with archive (saves current PostgreSQL state before overwriting)
    python db_config/sync.py upload --archive

    # Sync only prompts or only registry
    python db_config/sync.py download --prompts-only
    python db_config/sync.py download --registry-only

    # Dry run (show what would happen without making changes)
    python db_config/sync.py upload --dry-run

    # Filter by model (prompts) or source (registry)
    python db_config/sync.py download --model iris
    python db_config/sync.py download --source internal

Folder Structure:
    db_config/
    ├── sync.py                     # This script
    ├── backups/
    │   ├── prompts/
    │   │   └── {model}/
    │   │       └── {layer}/
    │   │           └── {name}.md
    │   └── registry/
    │       └── {db_name}.yaml
    └── archive/
        └── {timestamp}/
            ├── prompts/...
            └── registry/...
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local", override=True)
except ImportError:
    pass

# Database connection settings
DB_HOST = os.getenv("VECTOR_POSTGRES_DB_HOST", "localhost")
DB_PORT = os.getenv("VECTOR_POSTGRES_DB_PORT", "34532")
DB_NAME = os.getenv("VECTOR_POSTGRES_DB_NAME", "maven-finance")
DB_USER = os.getenv("VECTOR_POSTGRES_DB_USERNAME", os.getenv("USER", "postgres"))
DB_PASSWORD = os.getenv("VECTOR_POSTGRES_DB_PASSWORD", "")
DB_GSSENCMODE = os.getenv("PGGSSENCMODE", "")
DB_SSLMODE = os.getenv("PGSSLMODE", "")

# Paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS_DIR = os.path.join(SCRIPT_DIR, "backups")
PROMPTS_DIR = os.path.join(BACKUPS_DIR, "prompts")
REGISTRY_DIR = os.path.join(BACKUPS_DIR, "registry")
ARCHIVE_DIR = os.path.join(SCRIPT_DIR, "archive")


def get_connection():
    """Create database connection."""
    kwargs = dict(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    if DB_GSSENCMODE:
        kwargs["gssencmode"] = DB_GSSENCMODE
    if DB_SSLMODE:
        kwargs["sslmode"] = DB_SSLMODE
    return psycopg2.connect(**kwargs)


# =============================================================================
# ARCHIVE FUNCTIONS
# =============================================================================

def archive_backups(timestamp: str):
    """Archive current backups folder before downloading new data."""
    if not os.path.exists(BACKUPS_DIR):
        return

    # Check if there's anything to archive
    has_content = False
    for root, dirs, files in os.walk(BACKUPS_DIR):
        if files:
            has_content = True
            break

    if not has_content:
        return

    archive_path = os.path.join(ARCHIVE_DIR, f"backups_{timestamp}")
    os.makedirs(archive_path, exist_ok=True)

    # Copy backups to archive
    for item in ["prompts", "registry"]:
        src = os.path.join(BACKUPS_DIR, item)
        if os.path.exists(src):
            dst = os.path.join(archive_path, item)
            shutil.copytree(src, dst)

    print(f"Archived existing backups to: {archive_path}")


def archive_from_postgres(conn, timestamp: str):
    """Archive current PostgreSQL state before uploading new data."""
    archive_path = os.path.join(ARCHIVE_DIR, f"postgres_{timestamp}")
    os.makedirs(archive_path, exist_ok=True)

    # Archive prompts
    prompts_path = os.path.join(archive_path, "prompts")
    os.makedirs(prompts_path, exist_ok=True)
    download_prompts(conn, prompts_path)

    # Archive registry
    registry_path = os.path.join(archive_path, "registry")
    os.makedirs(registry_path, exist_ok=True)
    download_registry(conn, registry_path)

    print(f"Archived PostgreSQL state to: {archive_path}")


# =============================================================================
# PROMPTS - DOWNLOAD
# =============================================================================

def fetch_all_prompts(conn, model_filter: Optional[str] = None) -> List[Dict]:
    """Fetch all prompts from the database."""
    cursor = conn.cursor()

    if model_filter:
        cursor.execute(
            """
            SELECT model, layer, name, version, description,
                   system_prompt, user_prompt, tool_definition
            FROM prompts
            WHERE model = %s
            ORDER BY model, layer, name, version DESC
            """,
            (model_filter,)
        )
    else:
        cursor.execute(
            """
            SELECT model, layer, name, version, description,
                   system_prompt, user_prompt, tool_definition
            FROM prompts
            ORDER BY model, layer, name, version DESC
            """
        )

    columns = ['model', 'layer', 'name', 'version', 'description',
               'system_prompt', 'user_prompt', 'tool_definition']

    prompts = []
    seen = set()

    for row in cursor.fetchall():
        prompt = dict(zip(columns, row))
        key = (prompt['model'], prompt['layer'], prompt['name'])

        if key not in seen:
            seen.add(key)
            prompts.append(prompt)

    cursor.close()
    return prompts


def format_prompt_markdown(prompt: Dict) -> str:
    """Format a prompt as a readable markdown file."""
    lines = []

    # Header
    lines.append(f"# {prompt['name']}")
    lines.append("")
    lines.append(f"**Model:** {prompt['model']}")
    lines.append(f"**Layer:** {prompt['layer']}")
    lines.append(f"**Version:** {prompt['version']}")
    if prompt['description']:
        lines.append(f"**Description:** {prompt['description']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # System Prompt
    lines.append("## System Prompt")
    lines.append("")
    if prompt['system_prompt']:
        lines.append("```")
        lines.append(prompt['system_prompt'])
        lines.append("```")
    else:
        lines.append("*No system prompt defined*")
    lines.append("")

    # User Prompt
    lines.append("## User Prompt")
    lines.append("")
    if prompt['user_prompt']:
        lines.append("```")
        lines.append(prompt['user_prompt'])
        lines.append("```")
    else:
        lines.append("*No user prompt defined*")
    lines.append("")

    # Tool Definition
    lines.append("## Tool Definition")
    lines.append("")
    if prompt['tool_definition']:
        lines.append("```json")
        if isinstance(prompt['tool_definition'], dict):
            lines.append(json.dumps(prompt['tool_definition'], indent=2))
        else:
            try:
                tool_dict = json.loads(prompt['tool_definition'])
                lines.append(json.dumps(tool_dict, indent=2))
            except (json.JSONDecodeError, TypeError):
                lines.append(str(prompt['tool_definition']))
        lines.append("```")
    else:
        lines.append("*No tool definition*")
    lines.append("")

    return "\n".join(lines)


def download_prompts(conn, output_dir: str, model_filter: Optional[str] = None) -> int:
    """Download prompts from PostgreSQL to files."""
    prompts = fetch_all_prompts(conn, model_filter)

    count = 0
    for prompt in prompts:
        model = prompt['model']
        layer = prompt['layer']
        name = prompt['name']

        prompt_dir = os.path.join(output_dir, model, layer)
        os.makedirs(prompt_dir, exist_ok=True)

        file_path = os.path.join(prompt_dir, f"{name}.md")
        content = format_prompt_markdown(prompt)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        count += 1

    return count


# =============================================================================
# PROMPTS - UPLOAD
# =============================================================================

def parse_prompt_markdown(file_path: str) -> Dict:
    """Parse a prompt markdown file and extract all fields."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    prompt = {
        'model': None,
        'layer': None,
        'name': None,
        'version': '1.0.0',
        'description': None,
        'system_prompt': None,
        'user_prompt': None,
        'tool_definition': None,
    }

    # Extract name from title
    name_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if name_match:
        prompt['name'] = name_match.group(1).strip()

    # Extract metadata
    model_match = re.search(r'\*\*Model:\*\* (.+)$', content, re.MULTILINE)
    if model_match:
        prompt['model'] = model_match.group(1).strip()

    layer_match = re.search(r'\*\*Layer:\*\* (.+)$', content, re.MULTILINE)
    if layer_match:
        prompt['layer'] = layer_match.group(1).strip()

    version_match = re.search(r'\*\*Version:\*\* (.+)$', content, re.MULTILINE)
    if version_match:
        prompt['version'] = version_match.group(1).strip()

    desc_match = re.search(r'\*\*Description:\*\* (.+)$', content, re.MULTILINE)
    if desc_match:
        prompt['description'] = desc_match.group(1).strip()

    # Extract sections
    prompt['system_prompt'] = extract_section_content(content, "System Prompt")
    prompt['user_prompt'] = extract_section_content(content, "User Prompt")

    tool_def = extract_section_content(content, "Tool Definition", is_json=True)
    if tool_def:
        try:
            prompt['tool_definition'] = json.loads(tool_def)
        except json.JSONDecodeError:
            prompt['tool_definition'] = None

    return prompt


def extract_section_content(content: str, section_name: str, is_json: bool = False) -> Optional[str]:
    """Extract content from a markdown section."""
    section_pattern = rf'^## {re.escape(section_name)}\s*$'
    section_match = re.search(section_pattern, content, re.MULTILINE)

    if not section_match:
        return None

    after_header = content[section_match.end():]

    if after_header.strip().startswith("*No "):
        return None

    if is_json:
        code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    else:
        code_block_pattern = r'```\s*\n(.*?)\n```'

    code_match = re.search(code_block_pattern, after_header, re.DOTALL)

    if code_match:
        return code_match.group(1)

    return None


def upload_prompt(conn, prompt: Dict, dry_run: bool = False) -> str:
    """Upload a single prompt to PostgreSQL."""
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM prompts WHERE model = %s AND layer = %s AND name = %s",
        (prompt['model'], prompt['layer'], prompt['name'])
    )
    existing = cursor.fetchone()

    tool_def = prompt['tool_definition']
    if isinstance(tool_def, dict):
        tool_def = json.dumps(tool_def)

    if existing:
        action = "UPDATE"
        if not dry_run:
            cursor.execute(
                """
                UPDATE prompts
                SET description = %s, system_prompt = %s, user_prompt = %s,
                    tool_definition = %s, version = %s
                WHERE model = %s AND layer = %s AND name = %s
                """,
                (prompt['description'], prompt['system_prompt'], prompt['user_prompt'],
                 tool_def, prompt['version'],
                 prompt['model'], prompt['layer'], prompt['name'])
            )
    else:
        action = "INSERT"
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO prompts (model, layer, name, version, description,
                                     system_prompt, user_prompt, tool_definition)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (prompt['model'], prompt['layer'], prompt['name'], prompt['version'],
                 prompt['description'], prompt['system_prompt'], prompt['user_prompt'],
                 tool_def)
            )

    cursor.close()
    return action


def upload_prompts(conn, input_dir: str, model_filter: Optional[str] = None, dry_run: bool = False) -> tuple:
    """Upload prompts from files to PostgreSQL."""
    updated = 0
    inserted = 0
    errors = 0

    for root, _, files in os.walk(input_dir):
        for filename in files:
            if not filename.endswith('.md'):
                continue

            file_path = os.path.join(root, filename)

            try:
                prompt = parse_prompt_markdown(file_path)

                if not all([prompt['model'], prompt['layer'], prompt['name']]):
                    print(f"  SKIP: {file_path} - missing required fields")
                    errors += 1
                    continue

                if model_filter and prompt['model'] != model_filter:
                    continue

                action = upload_prompt(conn, prompt, dry_run)

                if action == "UPDATE":
                    updated += 1
                else:
                    inserted += 1

                print(f"  {action}: {prompt['model']}/{prompt['layer']}/{prompt['name']}")

            except Exception as e:
                print(f"  ERROR: {file_path} - {e}")
                errors += 1

    return updated, inserted, errors


# =============================================================================
# REGISTRY - DOWNLOAD
# =============================================================================

def fetch_all_registry(conn, source_filter: Optional[str] = None) -> List[Dict]:
    """Fetch all database registry entries from PostgreSQL."""
    cursor = conn.cursor()

    if source_filter:
        cursor.execute(
            """
            SELECT db_source, db_name, db_summary, db_description,
                   batch_size, max_selected_files,
                   top_chunks_in_catalog_selection, top_chunks_in_metadata_research,
                   page_threshold_for_full_content, enable_db_wide_deep_research,
                   max_parallel_files, max_chunks_per_file,
                   max_pages_for_full_context, max_primary_section_page_count,
                   max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages,
                   metadata_context_fields, search_modes, catalog_config,
                   semantic_config, metadata_config, sample_questions,
                   enabled, ad_groups
            FROM iris_database_registry
            WHERE db_source LIKE %s
            ORDER BY db_name
            """,
            (f"{source_filter}%",)
        )
    else:
        cursor.execute(
            """
            SELECT db_source, db_name, db_summary, db_description,
                   batch_size, max_selected_files,
                   top_chunks_in_catalog_selection, top_chunks_in_metadata_research,
                   page_threshold_for_full_content, enable_db_wide_deep_research,
                   max_parallel_files, max_chunks_per_file,
                   max_pages_for_full_context, max_primary_section_page_count,
                   max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages,
                   metadata_context_fields, search_modes, catalog_config,
                   semantic_config, metadata_config, sample_questions,
                   enabled, ad_groups
            FROM iris_database_registry
            ORDER BY db_name
            """
        )

    columns = ['db_source', 'db_name', 'db_summary', 'db_description',
               'batch_size', 'max_selected_files',
               'top_chunks_in_catalog_selection', 'top_chunks_in_metadata_research',
               'page_threshold_for_full_content', 'enable_db_wide_deep_research',
               'max_parallel_files', 'max_chunks_per_file',
               'max_pages_for_full_context', 'max_primary_section_page_count',
               'max_subsection_page_count', 'max_neighbour_chunks', 'max_gap_fill_pages',
               'metadata_context_fields', 'search_modes', 'catalog_config',
               'semantic_config', 'metadata_config', 'sample_questions',
               'enabled', 'ad_groups']

    entries = []
    for row in cursor.fetchall():
        entry = dict(zip(columns, row))
        entries.append(entry)

    cursor.close()
    return entries


def format_registry_yaml(entry: Dict) -> str:
    """Format a registry entry as YAML."""
    # Create ordered dict for nice output
    output = {
        'db_source': entry['db_source'],
        'db_name': entry['db_name'],
        'db_summary': entry['db_summary'],
        'db_description': entry['db_description'],
        'enabled': entry['enabled'],
        'search_modes': entry['search_modes'],
        'ad_groups': entry['ad_groups'],
        # Research configuration - individual fields
        'batch_size': entry['batch_size'],
        'max_selected_files': entry['max_selected_files'],
        'top_chunks_in_catalog_selection': entry['top_chunks_in_catalog_selection'],
        'top_chunks_in_metadata_research': entry['top_chunks_in_metadata_research'],
        'page_threshold_for_full_content': entry['page_threshold_for_full_content'],
        'enable_db_wide_deep_research': entry['enable_db_wide_deep_research'],
        'max_parallel_files': entry['max_parallel_files'],
        'max_chunks_per_file': entry['max_chunks_per_file'],
        'max_pages_for_full_context': entry['max_pages_for_full_context'],
        'max_primary_section_page_count': entry['max_primary_section_page_count'],
        'max_subsection_page_count': entry['max_subsection_page_count'],
        'max_neighbour_chunks': entry['max_neighbour_chunks'],
        'max_gap_fill_pages': entry['max_gap_fill_pages'],
        'metadata_context_fields': entry['metadata_context_fields'],
        # Other configs
        'catalog_config': entry['catalog_config'],
        'semantic_config': entry['semantic_config'],
        'metadata_config': entry['metadata_config'],
        'sample_questions': entry['sample_questions'],
    }

    return yaml.dump(output, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)


def download_registry(conn, output_dir: str, source_filter: Optional[str] = None) -> int:
    """Download registry entries from PostgreSQL to files."""
    entries = fetch_all_registry(conn, source_filter)

    os.makedirs(output_dir, exist_ok=True)

    count = 0
    for entry in entries:
        db_source = entry['db_source']
        file_path = os.path.join(output_dir, f"{db_source}.yaml")
        content = format_registry_yaml(entry)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        count += 1

    return count


# =============================================================================
# REGISTRY - UPLOAD
# =============================================================================

def parse_registry_yaml(file_path: str) -> Dict:
    """Parse a registry YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def upload_registry_entry(conn, entry: Dict, dry_run: bool = False) -> str:
    """Upload a single registry entry to PostgreSQL."""
    cursor = conn.cursor()

    cursor.execute(
        "SELECT db_source FROM iris_database_registry WHERE db_source = %s",
        (entry['db_source'],)
    )
    existing = cursor.fetchone()

    if existing:
        action = "UPDATE"
        if not dry_run:
            cursor.execute(
                """
                UPDATE iris_database_registry
                SET db_name = %s, db_summary = %s, db_description = %s,
                    batch_size = %s, max_selected_files = %s,
                    top_chunks_in_catalog_selection = %s, top_chunks_in_metadata_research = %s,
                    page_threshold_for_full_content = %s, enable_db_wide_deep_research = %s,
                    max_parallel_files = %s, max_chunks_per_file = %s,
                    max_pages_for_full_context = %s, max_primary_section_page_count = %s,
                    max_subsection_page_count = %s, max_neighbour_chunks = %s, max_gap_fill_pages = %s,
                    metadata_context_fields = %s,
                    search_modes = %s, catalog_config = %s,
                    semantic_config = %s, metadata_config = %s, sample_questions = %s,
                    enabled = %s, ad_groups = %s, updated_at = NOW()
                WHERE db_source = %s
                """,
                (entry['db_name'], entry['db_summary'], entry['db_description'],
                 entry['batch_size'], entry['max_selected_files'],
                 entry['top_chunks_in_catalog_selection'], entry['top_chunks_in_metadata_research'],
                 entry['page_threshold_for_full_content'], entry['enable_db_wide_deep_research'],
                 entry['max_parallel_files'], entry['max_chunks_per_file'],
                 entry.get('max_pages_for_full_context', 6),
                 entry.get('max_primary_section_page_count', 6),
                 entry.get('max_subsection_page_count', 3),
                 entry.get('max_neighbour_chunks', 2),
                 entry.get('max_gap_fill_pages', 2),
                 entry.get('metadata_context_fields', ['document_summary']),
                 entry.get('search_modes'),
                 json.dumps(entry.get('catalog_config')) if entry.get('catalog_config') else None,
                 json.dumps(entry.get('semantic_config')) if entry.get('semantic_config') else None,
                 json.dumps(entry.get('metadata_config')) if entry.get('metadata_config') else None,
                 json.dumps(entry.get('sample_questions')) if entry.get('sample_questions') else None,
                 entry.get('enabled', True), entry.get('ad_groups'),
                 entry['db_source'])
            )
    else:
        action = "INSERT"
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO iris_database_registry
                    (db_source, db_name, db_summary, db_description,
                     batch_size, max_selected_files,
                     top_chunks_in_catalog_selection, top_chunks_in_metadata_research,
                     page_threshold_for_full_content, enable_db_wide_deep_research,
                     max_parallel_files, max_chunks_per_file,
                     max_pages_for_full_context, max_primary_section_page_count,
                     max_subsection_page_count, max_neighbour_chunks, max_gap_fill_pages,
                     metadata_context_fields,
                     search_modes, catalog_config, semantic_config, metadata_config,
                     sample_questions, enabled, ad_groups)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (entry['db_source'], entry['db_name'], entry['db_summary'], entry['db_description'],
                 entry['batch_size'], entry['max_selected_files'],
                 entry['top_chunks_in_catalog_selection'], entry['top_chunks_in_metadata_research'],
                 entry['page_threshold_for_full_content'], entry['enable_db_wide_deep_research'],
                 entry['max_parallel_files'], entry['max_chunks_per_file'],
                 entry.get('max_pages_for_full_context', 6),
                 entry.get('max_primary_section_page_count', 6),
                 entry.get('max_subsection_page_count', 3),
                 entry.get('max_neighbour_chunks', 2),
                 entry.get('max_gap_fill_pages', 2),
                 entry.get('metadata_context_fields', ['document_summary']),
                 entry.get('search_modes'),
                 json.dumps(entry.get('catalog_config')) if entry.get('catalog_config') else None,
                 json.dumps(entry.get('semantic_config')) if entry.get('semantic_config') else None,
                 json.dumps(entry.get('metadata_config')) if entry.get('metadata_config') else None,
                 json.dumps(entry.get('sample_questions')) if entry.get('sample_questions') else None,
                 entry.get('enabled', True), entry.get('ad_groups'))
            )

    cursor.close()
    return action


def upload_registry(conn, input_dir: str, source_filter: Optional[str] = None, dry_run: bool = False) -> tuple:
    """Upload registry entries from files to PostgreSQL."""
    updated = 0
    inserted = 0
    errors = 0

    for filename in os.listdir(input_dir):
        if not filename.endswith('.yaml'):
            continue

        file_path = os.path.join(input_dir, filename)

        try:
            entry = parse_registry_yaml(file_path)

            if not entry.get('db_source'):
                print(f"  SKIP: {file_path} - missing db_source")
                errors += 1
                continue

            if source_filter and not entry['db_source'].startswith(source_filter):
                continue

            action = upload_registry_entry(conn, entry, dry_run)

            if action == "UPDATE":
                updated += 1
            else:
                inserted += 1

            print(f"  {action}: {entry['db_source']}")

        except Exception as e:
            print(f"  ERROR: {file_path} - {e}")
            errors += 1

    return updated, inserted, errors


# =============================================================================
# MAIN COMMANDS
# =============================================================================

def cmd_download(args):
    """Download data from PostgreSQL to backup files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    try:
        conn = get_connection()
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    try:
        # Archive if requested
        if args.archive:
            archive_backups(timestamp)

        # Clear existing backups (download is a full refresh)
        if not args.prompts_only and not args.registry_only:
            # Clear both
            if os.path.exists(PROMPTS_DIR):
                shutil.rmtree(PROMPTS_DIR)
            if os.path.exists(REGISTRY_DIR):
                shutil.rmtree(REGISTRY_DIR)
        elif args.prompts_only:
            if os.path.exists(PROMPTS_DIR):
                shutil.rmtree(PROMPTS_DIR)
        elif args.registry_only:
            if os.path.exists(REGISTRY_DIR):
                shutil.rmtree(REGISTRY_DIR)

        os.makedirs(PROMPTS_DIR, exist_ok=True)
        os.makedirs(REGISTRY_DIR, exist_ok=True)

        # Download prompts
        if not args.registry_only:
            print("\nDownloading prompts...")
            count = download_prompts(conn, PROMPTS_DIR, args.model)
            print(f"  Downloaded {count} prompts to {PROMPTS_DIR}")

        # Download registry
        if not args.prompts_only:
            print("\nDownloading registry...")
            count = download_registry(conn, REGISTRY_DIR, args.source)
            print(f"  Downloaded {count} registry entries to {REGISTRY_DIR}")

        print("\nDownload complete!")

    finally:
        conn.close()


def cmd_upload(args):
    """Upload data from backup files to PostgreSQL."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    if args.dry_run:
        print("\n[DRY RUN - No changes will be made]\n")

    try:
        conn = get_connection()
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    try:
        # Archive PostgreSQL state if requested
        if args.archive and not args.dry_run:
            archive_from_postgres(conn, timestamp)

        total_updated = 0
        total_inserted = 0
        total_errors = 0

        # Upload prompts
        if not args.registry_only and os.path.exists(PROMPTS_DIR):
            print("\nUploading prompts...")
            updated, inserted, errors = upload_prompts(conn, PROMPTS_DIR, args.model, args.dry_run)
            total_updated += updated
            total_inserted += inserted
            total_errors += errors

        # Upload registry
        if not args.prompts_only and os.path.exists(REGISTRY_DIR):
            print("\nUploading registry...")
            updated, inserted, errors = upload_registry(conn, REGISTRY_DIR, args.source, args.dry_run)
            total_updated += updated
            total_inserted += inserted
            total_errors += errors

        if not args.dry_run:
            conn.commit()

        print(f"\nUpload complete!")
        print(f"  Updated: {total_updated}")
        print(f"  Inserted: {total_inserted}")
        print(f"  Errors: {total_errors}")

        if args.dry_run:
            print("\n[DRY RUN - No changes were made]")

    finally:
        conn.close()


def cmd_status(args):
    """Show status of backups and PostgreSQL."""
    print(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"Backups:  {BACKUPS_DIR}")
    print(f"Archive:  {ARCHIVE_DIR}")

    # Count backup files
    prompt_count = 0
    registry_count = 0

    if os.path.exists(PROMPTS_DIR):
        for root, _, files in os.walk(PROMPTS_DIR):
            prompt_count += len([f for f in files if f.endswith('.md')])

    if os.path.exists(REGISTRY_DIR):
        registry_count = len([f for f in os.listdir(REGISTRY_DIR) if f.endswith('.yaml')])

    print(f"\nBackup files:")
    print(f"  Prompts:  {prompt_count}")
    print(f"  Registry: {registry_count}")

    # Count database entries
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM prompts")
        db_prompts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM iris_database_registry")
        db_registry = cursor.fetchone()[0]

        print(f"\nPostgreSQL:")
        print(f"  Prompts:  {db_prompts}")
        print(f"  Registry: {db_registry}")

        conn.close()
    except psycopg2.Error as e:
        print(f"\nPostgreSQL: Unable to connect ({e})")

    # Count archives
    if os.path.exists(ARCHIVE_DIR):
        archives = os.listdir(ARCHIVE_DIR)
        print(f"\nArchives: {len(archives)}")
        for archive in sorted(archives)[-5:]:  # Show last 5
            print(f"  {archive}")


def main():
    parser = argparse.ArgumentParser(
        description="IRIS Database Configuration Sync Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s download                    Download all from PostgreSQL
  %(prog)s upload                      Upload all to PostgreSQL
  %(prog)s download --archive          Archive backups before downloading
  %(prog)s upload --archive --dry-run  Preview upload with PostgreSQL archive
  %(prog)s status                      Show current status
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Download command
    dl = subparsers.add_parser('download', help='Download from PostgreSQL to backup files')
    dl.add_argument('--archive', '-a', action='store_true',
                    help='Archive existing backups before downloading')
    dl.add_argument('--prompts-only', action='store_true',
                    help='Download only prompts')
    dl.add_argument('--registry-only', action='store_true',
                    help='Download only registry')
    dl.add_argument('--model', '-m', help='Filter prompts by model (e.g., iris)')
    dl.add_argument('--source', '-s', help='Filter registry by source prefix (e.g., internal)')

    # Upload command
    ul = subparsers.add_parser('upload', help='Upload from backup files to PostgreSQL')
    ul.add_argument('--archive', '-a', action='store_true',
                    help='Archive PostgreSQL state before uploading')
    ul.add_argument('--dry-run', '-n', action='store_true',
                    help='Show what would happen without making changes')
    ul.add_argument('--prompts-only', action='store_true',
                    help='Upload only prompts')
    ul.add_argument('--registry-only', action='store_true',
                    help='Upload only registry')
    ul.add_argument('--model', '-m', help='Filter prompts by model (e.g., iris)')
    ul.add_argument('--source', '-s', help='Filter registry by source prefix (e.g., internal)')

    # Status command
    subparsers.add_parser('status', help='Show status of backups and PostgreSQL')

    args = parser.parse_args()

    if args.command == 'download':
        cmd_download(args)
    elif args.command == 'upload':
        cmd_upload(args)
    elif args.command == 'status':
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
