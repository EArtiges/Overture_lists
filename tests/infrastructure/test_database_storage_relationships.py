"""
Tests for DatabaseStorage relationship operations.
"""
import pytest


@pytest.mark.database
class TestDatabaseStorageRelationships:
    """Test organizational hierarchy relationship functionality."""

    def test_add_relationship(self, populated_test_db):
        """Test creating a relationship between divisions."""
        divisions = populated_test_db.get_all_divisions()
        parent_id = divisions[1]['id']  # California
        child_id = divisions[2]['id']    # LA County

        populated_test_db.add_relationship(
            parent_division_id=parent_id,
            child_division_id=child_id,
            relationship_type="reports_to"
        )

        # Verify it was created
        rels = populated_test_db.get_relationships(parent_id)
        assert len(rels) > 0
        assert any(r['parent_division_id'] == parent_id and r['child_division_id'] == child_id for r in rels)

    def test_get_relationships_for_division(self, populated_test_db):
        """Test retrieving relationships for a division."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Get relationships where division 0 is involved
        relationships = populated_test_db.get_relationships(divisions[0]['id'])
        assert len(relationships) > 0
        assert any(r['parent_division_id'] == divisions[0]['id'] for r in relationships)

    def test_get_children_for_parent(self, populated_test_db):
        """Test retrieving all children for a parent division."""
        divisions = populated_test_db.get_all_divisions()
        parent_id = divisions[0]['id']  # US

        # Create two child relationships
        populated_test_db.add_relationship(
            parent_division_id=parent_id,
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )
        populated_test_db.add_relationship(
            parent_division_id=parent_id,
            child_division_id=divisions[2]['id'],
            relationship_type="reports_to"
        )

        # Get all relationships and filter for children
        all_rels = populated_test_db.get_relationships(parent_id)
        children = [r for r in all_rels if r['parent_division_id'] == parent_id]
        assert len(children) == 2

    def test_get_parents_for_child(self, populated_test_db):
        """Test retrieving all parents for a child division (many-to-many)."""
        divisions = populated_test_db.get_all_divisions()
        child_id = divisions[2]['id']  # LA County

        # Create two parent relationships (child can have multiple parents)
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=child_id,
            relationship_type="reports_to"
        )
        populated_test_db.add_relationship(
            parent_division_id=divisions[1]['id'],
            child_division_id=child_id,
            relationship_type="reports_to"
        )

        # Get all relationships and filter for parents
        all_rels = populated_test_db.get_relationships(child_id)
        parents = [r for r in all_rels if r['child_division_id'] == child_id]
        assert len(parents) == 2

    def test_relationship_type_reports_to(self, populated_test_db):
        """Test creating 'reports_to' relationship."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        rels = populated_test_db.get_relationships(divisions[0]['id'])
        assert any(r['relationship_type'] == "reports_to" for r in rels)

    def test_relationship_type_collaborates_with(self, populated_test_db):
        """Test creating 'collaborates_with' relationship."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="collaborates_with"
        )

        rels = populated_test_db.get_relationships(divisions[0]['id'])
        assert any(r['relationship_type'] == "collaborates_with" for r in rels)

    def test_unique_constraint(self, populated_test_db):
        """Test that (parent, child, type) tuple is unique (INSERT OR IGNORE)."""
        divisions = populated_test_db.get_all_divisions()

        # Create first relationship
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        rels_before = populated_test_db.get_relationships(divisions[0]['id'])
        count_before = len(rels_before)

        # Try to create duplicate (same parent, child, type) - should be ignored
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Verify no duplicate was created
        rels_after = populated_test_db.get_relationships(divisions[0]['id'])
        assert len(rels_after) == count_before  # Count should be same

    def test_can_have_multiple_relationship_types(self, populated_test_db):
        """Test that same pair can have multiple relationship types."""
        divisions = populated_test_db.get_all_divisions()

        # Create first relationship type
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Create second relationship type for same pair
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="collaborates_with"
        )

        # Verify both exist
        rels = populated_test_db.get_relationships(divisions[0]['id'])
        types = [r['relationship_type'] for r in rels]
        assert "reports_to" in types
        assert "collaborates_with" in types
        assert len(rels) == 2  # Should have both relationship types

    def test_delete_relationship(self, populated_test_db):
        """Test deleting a relationship."""
        divisions = populated_test_db.get_all_divisions()

        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Verify it exists
        rels = populated_test_db.get_relationships(divisions[0]['id'])
        assert len(rels) > 0

        # Delete it using parent, child, type
        populated_test_db.delete_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Verify it's gone
        rels = populated_test_db.get_relationships(divisions[0]['id'])
        assert len(rels) == 0

    def test_cascade_delete_when_division_deleted(self, test_db):
        """Test that deleting a division cascades to delete its relationships."""
        # Create two divisions
        div1_id = test_db.save_division(
            system_id="div-1",
            name="Division 1",
            subtype="region",
            country="US",
            geometry=None
        )
        div2_id = test_db.save_division(
            system_id="div-2",
            name="Division 2",
            subtype="region",
            country="US",
            geometry=None
        )

        # Create relationship
        test_db.add_relationship(
            parent_division_id=div1_id,
            child_division_id=div2_id,
            relationship_type="reports_to"
        )

        # Verify relationship exists
        rels = test_db.get_relationships(div1_id)
        assert len(rels) > 0

        # Delete parent division
        test_db.conn.execute("DELETE FROM divisions WHERE id = ?", (div1_id,))
        test_db.conn.commit()

        # Verify relationship is gone (CASCADE delete)
        rels = test_db.get_all_relationships()
        assert not any(r['parent_division_id'] == div1_id for r in rels)

    def test_cannot_create_self_relationship(self, populated_test_db):
        """Test that division cannot have relationship with itself (CHECK constraint)."""
        divisions = populated_test_db.get_all_divisions()

        # Try to create self-relationship
        with pytest.raises(Exception):  # CHECK constraint: parent_division_id != child_division_id
            populated_test_db.add_relationship(
                parent_division_id=divisions[0]['id'],
                child_division_id=divisions[0]['id'],
                relationship_type="reports_to"
            )

    def test_many_to_many_relationships_allowed(self, populated_test_db):
        """Test that divisions can have multiple parents and children."""
        divisions = populated_test_db.get_all_divisions()

        # Division 0 has two children
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[2]['id'],
            relationship_type="reports_to"
        )

        # Division 2 has two parents
        populated_test_db.add_relationship(
            parent_division_id=divisions[1]['id'],
            child_division_id=divisions[2]['id'],
            relationship_type="collaborates_with"
        )

        # Verify many-to-many
        rels_div0 = populated_test_db.get_relationships(divisions[0]['id'])
        children_of_div0 = [r for r in rels_div0 if r['parent_division_id'] == divisions[0]['id']]

        rels_div2 = populated_test_db.get_relationships(divisions[2]['id'])
        parents_of_div2 = [r for r in rels_div2 if r['child_division_id'] == divisions[2]['id']]

        assert len(children_of_div0) == 2  # Division 0 has 2 children
        assert len(parents_of_div2) == 2   # Division 2 has 2 parents

    def test_get_all_relationships(self, populated_test_db):
        """Test retrieving all relationships."""
        divisions = populated_test_db.get_all_divisions()

        # Create multiple relationships
        for i in range(2):
            populated_test_db.add_relationship(
                parent_division_id=divisions[0]['id'],
                child_division_id=divisions[i + 1]['id'],
                relationship_type="reports_to"
            )

        all_rels = populated_test_db.get_all_relationships()
        assert len(all_rels) >= 2
        assert all(r['parent_division_id'] for r in all_rels)
        assert all(r['child_division_id'] for r in all_rels)

    def test_empty_relationships_list(self, populated_test_db):
        """Test getting relationships for division with none."""
        divisions = populated_test_db.get_all_divisions()

        rels = populated_test_db.get_relationships(divisions[2]['id'])
        assert len(rels) == 0
