"""
Tests for SCIM attribute filtering according to RFC 7644.
"""
import pytest
from scim.utils.attribute_filter import AttributeFilter


class TestAttributeFilter:
    """Test cases for SCIM attribute filtering."""
    
    @pytest.fixture
    def sample_user_resource(self):
        """Sample user resource for testing."""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "2819c223-7f76-453a-919d-413861904646",
            "externalId": "701984",
            "userName": "bjensen@example.com",
            "name": {
                "formatted": "Ms. Barbara J Jensen, III",
                "familyName": "Jensen",
                "givenName": "Barbara",
                "middleName": "Jane",
                "honorificPrefix": "Ms.",
                "honorificSuffix": "III"
            },
            "displayName": "Babs Jensen",
            "nickName": "Babs",
            "profileUrl": "https://login.example.com/bjensen",
            "emails": [
                {
                    "value": "bjensen@example.com",
                    "type": "work",
                    "primary": True
                },
                {
                    "value": "babs@jensen.org",
                    "type": "home"
                }
            ],
            "addresses": [
                {
                    "type": "work",
                    "streetAddress": "100 Universal City Plaza",
                    "locality": "Hollywood",
                    "region": "CA",
                    "postalCode": "91608",
                    "country": "USA",
                    "formatted": "100 Universal City Plaza\nHollywood, CA 91608 USA",
                    "primary": True
                },
                {
                    "type": "home",
                    "streetAddress": "456 Hollywood Blvd",
                    "locality": "Hollywood",
                    "region": "CA",
                    "postalCode": "91608",
                    "country": "USA",
                    "formatted": "456 Hollywood Blvd\nHollywood, CA 91608 USA"
                }
            ],
            "phoneNumbers": [
                {
                    "value": "555-555-5555",
                    "type": "work"
                },
                {
                    "value": "555-555-4444",
                    "type": "mobile"
                }
            ],
            "userType": "Employee",
            "title": "Tour Guide",
            "preferredLanguage": "en-US",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "active": True,
            "password": "t1meMa$heen",
            "groups": [
                {
                    "value": "e9e30dba-f08f-4109-8486-d5c6a331660a",
                    "$ref": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
                    "display": "Tour Guides"
                }
            ],
            "meta": {
                "resourceType": "User",
                "created": "2010-01-23T04:56:22.000Z",
                "lastModified": "2011-05-13T04:42:34.000Z",
                "version": 'W/"3694e05e9dff590"',
                "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646"
            }
        }
    
    @pytest.fixture
    def sample_group_resource(self):
        """Sample group resource for testing."""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
            "displayName": "Tour Guides",
            "members": [
                {
                    "value": "2819c223-7f76-453a-919d-413861904646",
                    "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
                    "display": "Babs Jensen"
                },
                {
                    "value": "902c246b-6245-4190-8e05-00816be7344a",
                    "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
                    "display": "Mandy Pepperidge"
                }
            ],
            "meta": {
                "resourceType": "Group",
                "created": "2010-01-23T04:56:22.000Z",
                "lastModified": "2011-05-13T04:42:34.000Z",
                "version": 'W/"3694e05e9dff592"',
                "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a"
            }
        }
    
    def test_no_filtering(self, sample_user_resource):
        """Test that no filtering returns the original resource."""
        result = AttributeFilter.filter_resource(sample_user_resource)
        assert result == sample_user_resource
    
    def test_attributes_simple(self, sample_user_resource):
        """Test filtering with simple attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            attributes=["userName", "displayName"]
        )
        
        # Should include minimum set + requested attributes
        assert "schemas" in result
        assert "id" in result
        assert "meta" in result
        assert result["userName"] == "bjensen@example.com"
        assert result["displayName"] == "Babs Jensen"
        
        # Should not include unrequested attributes
        assert "emails" not in result
        assert "name" not in result
        assert "addresses" not in result
    
    def test_attributes_nested(self, sample_user_resource):
        """Test filtering with nested attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            attributes=["name.givenName", "name.familyName"]
        )
        
        # Should include minimum set + requested nested attributes
        assert "schemas" in result
        assert "id" in result
        assert "meta" in result
        assert "name" in result
        assert result["name"]["givenName"] == "Barbara"
        assert result["name"]["familyName"] == "Jensen"
        
        # Should not include other name sub-attributes
        assert "formatted" not in result["name"]
        assert "middleName" not in result["name"]
    
    def test_attributes_multi_valued(self, sample_user_resource):
        """Test filtering with multi-valued attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            attributes=["emails.value", "emails.type"]
        )
        
        # Should include emails with only requested sub-attributes
        assert "emails" in result
        assert len(result["emails"]) == 2
        assert result["emails"][0]["value"] == "bjensen@example.com"
        assert result["emails"][0]["type"] == "work"
        assert "primary" not in result["emails"][0]
    
    def test_excluded_attributes_simple(self, sample_user_resource):
        """Test filtering with simple excluded attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            excluded_attributes=["password", "active", "groups"]
        )
        
        # Should include all attributes except excluded
        assert "userName" in result
        assert "displayName" in result
        assert "emails" in result
        
        # Should not include excluded attributes
        assert "password" not in result
        assert "active" not in result
        assert "groups" not in result
    
    def test_excluded_attributes_nested(self, sample_user_resource):
        """Test filtering with nested excluded attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            excluded_attributes=["name.middleName", "name.honorificPrefix", "name.honorificSuffix"]
        )
        
        # Should include name but not excluded sub-attributes
        assert "name" in result
        assert "givenName" in result["name"]
        assert "familyName" in result["name"]
        assert "middleName" not in result["name"]
        assert "honorificPrefix" not in result["name"]
        assert "honorificSuffix" not in result["name"]
    
    def test_excluded_attributes_multi_valued(self, sample_user_resource):
        """Test filtering with excluded multi-valued attributes."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            excluded_attributes=["addresses.streetAddress", "addresses.postalCode"]
        )
        
        # Should include addresses but not excluded sub-attributes
        assert "addresses" in result
        assert len(result["addresses"]) == 2
        for address in result["addresses"]:
            assert "streetAddress" not in address
            assert "postalCode" not in address
            assert "locality" in address
            assert "region" in address
    
    def test_always_returned_attributes(self, sample_user_resource):
        """Test that always-returned attributes are never excluded."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            excluded_attributes=["schemas", "id", "meta"]
        )
        
        # These attributes should always be included
        assert "schemas" in result
        assert "id" in result
        assert "meta" in result
    
    def test_case_insensitive_attributes(self, sample_user_resource):
        """Test that attribute names are case-insensitive."""
        result = AttributeFilter.filter_resource(
            sample_user_resource,
            attributes=["USERNAME", "DisplayName", "name.GivenName"]
        )
        
        assert result["userName"] == "bjensen@example.com"
        assert result["displayName"] == "Babs Jensen"
        assert result["name"]["givenName"] == "Barbara"
    
    def test_filter_list_response(self, sample_user_resource, sample_group_resource):
        """Test filtering multiple resources in a list."""
        resources = [sample_user_resource, sample_group_resource]
        
        result = AttributeFilter.filter_list_response(
            resources,
            attributes=["displayName"]
        )
        
        assert len(result) == 2
        assert result[0]["displayName"] == "Babs Jensen"
        assert result[1]["displayName"] == "Tour Guides"
        assert "emails" not in result[0]
        assert "members" not in result[1]
    
    def test_extension_schema_filtering(self):
        """Test filtering with extension schemas."""
        resource = {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            ],
            "id": "2819c223",
            "userName": "bjensen",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": "701984",
                "costCenter": "4130",
                "organization": "Universal Studios",
                "division": "Theme Park",
                "department": "Tour Operations",
                "manager": {
                    "value": "26118915-6090-4610-87e4-49d8ca9f808d",
                    "displayName": "John Smith"
                }
            },
            "meta": {
                "resourceType": "User",
                "created": "2010-01-23T04:56:22.000Z",
                "lastModified": "2011-05-13T04:42:34.000Z"
            }
        }
        
        # Test including specific extension attributes
        result = AttributeFilter.filter_resource(
            resource,
            attributes=[
                "userName",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department"
            ]
        )
        
        assert result["userName"] == "bjensen"
        ext_schema = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
        assert ext_schema in result
        assert result[ext_schema]["employeeNumber"] == "701984"
        assert result[ext_schema]["department"] == "Tour Operations"
        assert "costCenter" not in result[ext_schema]
        assert "manager" not in result[ext_schema]
    
    def test_empty_multi_valued_attributes(self):
        """Test handling of empty multi-valued attributes."""
        resource = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "123",
            "userName": "test",
            "emails": [],
            "phoneNumbers": [],
            "meta": {
                "resourceType": "User",
                "created": "2010-01-23T04:56:22.000Z",
                "lastModified": "2011-05-13T04:42:34.000Z"
            }
        }
        
        result = AttributeFilter.filter_resource(
            resource,
            attributes=["emails", "phoneNumbers"]
        )
        
        # Empty arrays should be preserved
        assert "emails" in result
        assert result["emails"] == []
        assert "phoneNumbers" in result
        assert result["phoneNumbers"] == []