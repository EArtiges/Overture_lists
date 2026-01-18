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

        relationship_id = populated_test_db.add_relationship(
            parent_division_id=parent_id,
            child_division_id=child_id,
            relationship_type="reports_to"
        )

        assert relationship_id is not None
        assert isinstance(relationship_id, int)

    def test_get_relationship(self, populated_test_db):
        """Test retrieving a relationship by ID."""
        divisions = populated_test_db.get_all_divisions()

        rel_id = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        relationship = populated_test_db.get_relationship(rel_id)
        assert relationship is not None
        assert relationship['id'] == rel_id
        assert relationship['relationship_type'] == "reports_to"

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

        children = populated_test_db.get_child_relationships(parent_id)
        assert len(children) == 2
        assert all(c['parent_division_id'] == parent_id for c in children)

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

        parents = populated_test_db.get_parent_relationships(child_id)
        assert len(parents) == 2
        assert all(p['child_division_id'] == child_id for p in parents)

    def test_relationship_type_reports_to(self, populated_test_db):
        """Test creating 'reports_to' relationship."""
        divisions = populated_test_db.get_all_divisions()

        rel_id = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        rel = populated_test_db.get_relationship(rel_id)
        assert rel['relationship_type'] == "reports_to"

    def test_relationship_type_collaborates_with(self, populated_test_db):
        """Test creating 'collaborates_with' relationship."""
        divisions = populated_test_db.get_all_divisions()

        rel_id = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="collaborates_with"
        )

        rel = populated_test_db.get_relationship(rel_id)
        assert rel['relationship_type'] == "collaborates_with"

    def test_unique_constraint(self, populated_test_db):
        """Test that (parent, child, type) tuple must be unique."""
        divisions = populated_test_db.get_all_divisions()

        # Create first relationship
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Try to create duplicate (same parent, child, type)
        with pytest.raises(Exception):  # UNIQUE constraint violation
            populated_test_db.add_relationship(
                parent_division_id=divisions[0]['id'],
                child_division_id=divisions[1]['id'],
                relationship_type="reports_to"
            )

    def test_can_have_multiple_relationship_types(self, populated_test_db):
        """Test that same pair can have multiple relationship types."""
        divisions = populated_test_db.get_all_divisions()

        # Create first relationship type
        rel_id1 = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Create second relationship type for same pair
        rel_id2 = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="collaborates_with"
        )

        assert rel_id1 != rel_id2  # Different relationships

        # Verify both exist
        rel1 = populated_test_db.get_relationship(rel_id1)
        rel2 = populated_test_db.get_relationship(rel_id2)
        assert rel1['relationship_type'] != rel2['relationship_type']

    def test_delete_relationship(self, populated_test_db):
        """Test deleting a relationship."""
        divisions = populated_test_db.get_all_divisions()

        rel_id = populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )

        # Verify it exists
        assert populated_test_db.get_relationship(rel_id) is not None

        # Delete it
        populated_test_db.delete_relationship(rel_id)

        # Verify it's gone
        assert populated_test_db.get_relationship(rel_id) is None

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
        rel_id = test_db.add_relationship(
            parent_division_id=div1_id,
            child_division_id=div2_id,
            relationship_type="reports_to"
        )

        # Verify relationship exists
        assert test_db.get_relationship(rel_id) is not None

        # Delete parent division
        test_db.conn.execute("DELETE FROM divisions WHERE id = ?", (div1_id,))
        test_db.conn.commit()

        # Verify relationship is gone (CASCADE delete)
        assert test_db.get_relationship(rel_id) is None

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

        # Division 1 has two children
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
        # (Already has divisions[0] as parent from above)
        # Add another parent
        populated_test_db.add_relationship(
            parent_division_id=divisions[1]['id'],
            child_division_id=divisions[2]['id'],
            relationship_type="collaborates_with"
        )

        # Verify many-to-many
        children_of_div0 = populated_test_db.get_child_relationships(divisions[0]['id'])
        parents_of_div2 = populated_test_db.get_parent_relationships(divisions[2]['id'])

        assert len(children_of_div0) == 2  # Division 0 has 2 children
        assert len(parents_of_div2) == 2   # Division 2 has 2 parents

    def test_get_relationships_by_type(self, populated_test_db):
        """Test filtering relationships by type."""
        divisions = populated_test_db.get_all_divisions()

        # Create different types
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[1]['id'],
            relationship_type="reports_to"
        )
        populated_test_db.add_relationship(
            parent_division_id=divisions[0]['id'],
            child_division_id=divisions[2]['id'],
            relationship_type="collaborates_with"
        )

        reports_to = populated_test_db.get_child_relationships(
            divisions[0]['id'],
            relationship_type="reports_to"
        )
        collaborates = populated_test_db.get_child_relationships(
            divisions[0]['id'],
            relationship_type="collaborates_with"
        )

        assert len(reports_to) == 1
        assert len(collaborates) == 1
        assert reports_to[0]['relationship_type'] == "reports_to"
        assert collaborates[0]['relationship_type'] == "collaborates_with"

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

    def test_get_nonexistent_relationship(self, test_db):
        """Test retrieving relationship that doesn't exist."""
        result = test_db.get_relationship(99999)
        assert result is None

    def test_empty_children_list(self, populated_test_db):
        """Test getting children for division with no children."""
        divisions = populated_test_db.get_all_divisions()

        children = populated_test_db.get_child_relationships(divisions[2]['id'])
        assert len(children) == 0

    def test_empty_parents_list(self, populated_test_db):
        """Test getting parents for division with no parents."""
        divisions = populated_test_db.get_all_divisions()

        parents = populated_test_db.get_parent_relationships(divisions[0]['id'])
        assert len(parents) == 0
