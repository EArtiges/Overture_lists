#!/usr/bin/env python3
"""
Migrate existing JSON list files to SQLite database.

This script migrates:
- Boundary lists from ./list_data/ to database
- CRM client lists from ./crm_client_lists/ to database

Usage:
    python scripts/migrate_lists_to_db.py [--dry-run]
"""

import sys
import os
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.list_storage import ListStorage
from src.list_database_storage import ListDatabaseStorage


def migrate_lists(dry_run=False):
    """
    Migrate all JSON lists to database.

    Args:
        dry_run: If True, only print what would be migrated without actually doing it
    """
    print("=" * 60)
    print("LIST MIGRATION TO DATABASE")
    print("=" * 60)
    print()

    if dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()

    # Initialize database storage
    if not dry_run:
        db_storage = ListDatabaseStorage()
        print(f"✓ Database initialized at: {db_storage.db_path}")
    else:
        db_storage = None
        print(f"Would initialize database at: ./data/lists.db")

    print()

    # Migrate boundary lists
    print("BOUNDARY LISTS")
    print("-" * 60)

    json_storage = ListStorage(data_dir="./list_data")
    boundary_lists = json_storage.list_all_lists()

    if not boundary_lists:
        print("  No boundary lists found in ./list_data/")
    else:
        print(f"  Found {len(boundary_lists)} boundary list(s)")
        print()

        for idx, list_info in enumerate(boundary_lists, 1):
            list_data = json_storage.load_list(list_info['list_id'])
            if list_data:
                item_count = len(list_data.get('boundaries', []))
                print(f"  [{idx}] {list_data['list_name']}")
                print(f"      ID: {list_data['list_id']}")
                print(f"      Items: {item_count}")
                print(f"      Created: {list_data['created_at'][:10]}")

                if not dry_run:
                    try:
                        db_storage.save_list(
                            list_name=list_data['list_name'],
                            description=list_data.get('description', ''),
                            items=list_data['boundaries'],
                            list_type='boundary',
                            list_id=list_data['list_id']
                        )
                        print(f"      ✓ Migrated successfully")
                    except Exception as e:
                        print(f"      ✗ Error: {e}")
                else:
                    print(f"      → Would migrate to database")

                print()

    print()

    # Migrate CRM client lists
    print("CRM CLIENT LISTS")
    print("-" * 60)

    crm_storage = ListStorage(data_dir="./crm_client_lists")
    crm_lists = crm_storage.list_all_lists()

    if not crm_lists:
        print("  No CRM client lists found in ./crm_client_lists/")
    else:
        print(f"  Found {len(crm_lists)} CRM client list(s)")
        print()

        for idx, list_info in enumerate(crm_lists, 1):
            list_data = crm_storage.load_list(list_info['list_id'])
            if list_data:
                item_count = len(list_data.get('boundaries', []))
                print(f"  [{idx}] {list_data['list_name']}")
                print(f"      ID: {list_data['list_id']}")
                print(f"      Items: {item_count}")
                print(f"      Created: {list_data['created_at'][:10]}")

                if not dry_run:
                    try:
                        db_storage.save_list(
                            list_name=list_data['list_name'],
                            description=list_data.get('description', ''),
                            items=list_data['boundaries'],
                            list_type='crm_client',
                            list_id=list_data['list_id']
                        )
                        print(f"      ✓ Migrated successfully")
                    except Exception as e:
                        print(f"      ✗ Error: {e}")
                else:
                    print(f"      → Would migrate to database")

                print()

    print()
    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)

    if not dry_run:
        # Get final counts
        total_boundary = db_storage.get_list_count('boundary')
        total_crm = db_storage.get_list_count('crm_client')
        total_all = db_storage.get_list_count()

        print(f"  Boundary lists in database: {total_boundary}")
        print(f"  CRM client lists in database: {total_crm}")
        print(f"  Total lists in database: {total_all}")
        print()
        print(f"✓ Migration complete!")
        print()
        print("NOTE: Original JSON files have been preserved.")
        print("      They can be deleted after verifying the migration.")
    else:
        print(f"  Would migrate {len(boundary_lists)} boundary list(s)")
        print(f"  Would migrate {len(crm_lists)} CRM client list(s)")
        print(f"  Total: {len(boundary_lists) + len(crm_lists)} list(s)")
        print()
        print("Run without --dry-run to perform the migration.")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate JSON list files to SQLite database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )

    args = parser.parse_args()

    try:
        migrate_lists(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
