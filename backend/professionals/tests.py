import time

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from .models import Professional


class SingleCreateTests(TestCase):
    """Tests for POST /api/professionals/ — single create endpoint.
    Covers DESIGN.md test cases #1–#10."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/professionals/'
        self.valid_data = {
            'full_name': 'Alice Johnson',
            'email': 'alice@example.com',
            'phone': '555-0001',
            'company_name': 'Acme Corp',
            'job_title': 'Engineer',
            'source': 'direct',
        }

    # #1 — Valid data, all fields
    def test_create_valid_all_fields(self):
        """Valid data with all fields → 201, professional created."""
        res = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['full_name'], 'Alice Johnson')
        self.assertEqual(res.data['email'], 'alice@example.com')
        self.assertEqual(Professional.objects.count(), 1)

    # #2 — Missing full_name
    def test_create_missing_full_name(self):
        """Missing full_name → 400."""
        data = {**self.valid_data}
        del data['full_name']
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('full_name', res.data)

    # #3 — Missing source
    def test_create_missing_source(self):
        """Missing source → 400."""
        data = {**self.valid_data}
        del data['source']
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('source', res.data)

    # #4 — Invalid source value
    def test_create_invalid_source(self):
        """Invalid source value → 400."""
        data = {**self.valid_data, 'source': 'unknown'}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('source', res.data)

    # #5 — Duplicate email
    def test_create_duplicate_email(self):
        """Duplicate email → 400."""
        Professional.objects.create(**self.valid_data)
        data = {**self.valid_data, 'phone': '555-9999'}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)

    # #6 — Duplicate phone
    def test_create_duplicate_phone(self):
        """Duplicate phone → 400."""
        Professional.objects.create(**self.valid_data)
        data = {**self.valid_data, 'email': 'other@example.com'}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)

    # #7 — Invalid email format
    def test_create_invalid_email_format(self):
        """Invalid email format → 400."""
        data = {**self.valid_data, 'email': 'not-an-email'}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)

    # #8 — Email empty string, null, and omitted are all acceptable
    def test_create_email_empty_string(self):
        """Email as empty string → 201 (phone-only professional)."""
        data = {**self.valid_data, 'email': ''}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_email_null(self):
        """Email as null → 201 (phone-only professional)."""
        data = {**self.valid_data, 'email': None}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_email_omitted(self):
        """Email omitted entirely → 201 (phone-only professional)."""
        data = {**self.valid_data}
        del data['email']
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    # #9 — Very long full_name
    def test_create_long_full_name(self):
        """full_name > 255 chars → 400."""
        data = {**self.valid_data, 'full_name': 'A' * 256}
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('full_name', res.data)

    # #10 — Only required fields, optional fields default
    def test_create_only_required_fields(self):
        """Create with only required fields → 201, optional fields default to empty."""
        data = {
            'full_name': 'Minimal',
            'phone': '555-0010',
            'source': 'direct',
        }
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['company_name'], '')
        self.assertEqual(res.data['job_title'], '')
        self.assertIsNone(res.data['email'])


class BulkUpsertTests(TestCase):
    """Tests for POST /api/professionals/bulk — bulk upsert endpoint.
    Covers DESIGN.md test cases #11–#23."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/professionals/bulk'

    # #11 — All valid, all new
    def test_all_new_records(self):
        """All valid, all new → all in created[]."""
        data = [
            {'full_name': 'A', 'email': 'a@example.com', 'phone': '111', 'source': 'direct'},
            {'full_name': 'B', 'email': 'b@example.com', 'phone': '222', 'source': 'partner'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 2)
        self.assertEqual(len(res.data['updated']), 0)
        self.assertEqual(len(res.data['errors']), 0)

    # #12 — All existing by email
    def test_all_existing_by_email(self):
        """All valid, all existing by email → all in updated[]."""
        Professional.objects.create(
            full_name='A', email='a@example.com', phone='111', source='direct',
        )
        Professional.objects.create(
            full_name='B', email='b@example.com', phone='222', source='partner',
        )
        data = [
            {'full_name': 'A Updated', 'email': 'a@example.com', 'phone': '111', 'source': 'direct'},
            {'full_name': 'B Updated', 'email': 'b@example.com', 'phone': '222', 'source': 'partner'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 0)
        self.assertEqual(len(res.data['updated']), 2)
        self.assertEqual(res.data['updated'][0]['professional']['full_name'], 'A Updated')

    # #13 — Mix of new and existing
    def test_mix_new_and_existing(self):
        """Mix of new and existing → correct split across created[] and updated[]."""
        Professional.objects.create(
            full_name='Existing', email='existing@example.com', phone='111', source='direct',
        )
        data = [
            {'full_name': 'Existing Updated', 'email': 'existing@example.com', 'phone': '111', 'source': 'direct'},
            {'full_name': 'Brand New', 'email': 'new@example.com', 'phone': '222', 'source': 'partner'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 1)
        self.assertEqual(len(res.data['updated']), 1)
        self.assertEqual(res.data['updated'][0]['professional']['full_name'], 'Existing Updated')
        self.assertEqual(res.data['created'][0]['professional']['full_name'], 'Brand New')

    # #14 — One invalid among valid (partial success)
    def test_partial_success_one_invalid(self):
        """One invalid among valid → valid ones succeed, invalid in errors[]."""
        data = [
            {'full_name': 'Valid', 'email': 'v@example.com', 'phone': '111', 'source': 'direct'},
            {'full_name': '', 'email': 'bad@example.com', 'phone': '222', 'source': 'direct'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 1)
        self.assertEqual(len(res.data['errors']), 1)
        self.assertEqual(res.data['errors'][0]['index'], 1)

    # #15 — Email matches record A, phone matches record B → IntegrityError
    def test_cross_field_integrity_error(self):
        """Email matches A, phone matches B → IntegrityError on save."""
        Professional.objects.create(
            full_name='Record A', email='a@example.com', phone='111', source='direct',
        )
        Professional.objects.create(
            full_name='Record B', email='b@example.com', phone='222', source='direct',
        )
        # Lookup by email finds Record A, but phone 222 belongs to Record B
        data = [
            {'full_name': 'Conflict', 'email': 'a@example.com', 'phone': '222', 'source': 'direct'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['errors']), 1)
        self.assertEqual(len(res.data['created']), 0)
        self.assertEqual(len(res.data['updated']), 0)

    # #16 — Phone fallback when no email
    def test_phone_fallback_when_no_email(self):
        """Record with no email — falls back to phone lookup."""
        Professional.objects.create(
            full_name='Phone Only', phone='999', source='internal',
        )
        data = [
            {'full_name': 'Phone Updated', 'phone': '999', 'source': 'internal'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['updated']), 1)
        self.assertEqual(res.data['updated'][0]['professional']['full_name'], 'Phone Updated')

    # #17 — No email and no phone
    def test_no_email_no_phone_error(self):
        """Record with no email and no phone → error (phone is required by serializer)."""
        data = [
            {'full_name': 'No Contact', 'source': 'direct'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['errors']), 1)
        self.assertIn('phone', res.data['errors'][0]['errors'])

    # #18 — Two items in same batch with same email
    def test_duplicate_email_in_same_batch(self):
        """Two items with same email → first creates, second updates it."""
        data = [
            {'full_name': 'First', 'email': 'dup@example.com', 'phone': '111', 'source': 'direct'},
            {'full_name': 'Second', 'email': 'dup@example.com', 'phone': '111', 'source': 'direct'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 1)
        self.assertEqual(len(res.data['updated']), 1)
        # The final state should be 'Second'
        prof = Professional.objects.get(email='dup@example.com')
        self.assertEqual(prof.full_name, 'Second')

    # #19 — Empty list
    def test_empty_list(self):
        """Empty list [] → 200 with empty created/updated/errors."""
        res = self.client.post(self.url, [], format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 0)
        self.assertEqual(len(res.data['updated']), 0)
        self.assertEqual(len(res.data['errors']), 0)

    # #20 — Single item in list
    def test_single_item_in_list(self):
        """Single item in list → works like single create but with bulk response format."""
        data = [
            {'full_name': 'Solo', 'email': 'solo@example.com', 'phone': '111', 'source': 'direct'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 1)
        self.assertEqual(res.data['created'][0]['index'], 0)
        self.assertEqual(res.data['created'][0]['professional']['full_name'], 'Solo')

    # #21 — Upsert updates full_name but keeps other fields
    def test_upsert_partial_field_update(self):
        """Upsert updates full_name, other provided fields change, DB state is correct."""
        Professional.objects.create(
            full_name='Original Name',
            email='u@example.com',
            phone='111',
            company_name='Original Co',
            job_title='Original Title',
            source='direct',
        )
        data = [
            {
                'full_name': 'New Name',
                'email': 'u@example.com',
                'phone': '111',
                'company_name': 'New Co',
                'job_title': 'Original Title',
                'source': 'direct',
            },
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['updated']), 1)
        prof = Professional.objects.get(email='u@example.com')
        self.assertEqual(prof.full_name, 'New Name')
        self.assertEqual(prof.company_name, 'New Co')
        self.assertEqual(prof.job_title, 'Original Title')

    # #22 — No email, phone lookup, but update includes taken email → IntegrityError
    def test_phone_lookup_with_taken_email(self):
        """Phone lookup succeeds, but updating with an email that belongs to another record → error."""
        Professional.objects.create(
            full_name='Owner', email='taken@example.com', phone='111', source='direct',
        )
        Professional.objects.create(
            full_name='Phone Guy', phone='222', source='partner',
        )
        # Looks up by phone 222 (no email in lookup), but tries to set email to one already taken
        data = [
            {'full_name': 'Phone Guy Updated', 'email': 'taken@example.com', 'phone': '222', 'source': 'partner'},
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should error because email 'taken@example.com' already belongs to another record
        # The lookup is by email first (since email is provided), finds 'Owner', but phone 222 belongs to 'Phone Guy'
        self.assertEqual(len(res.data['errors']), 1)
        self.assertEqual(len(res.data['updated']), 0)

    # #23 — All records fail validation
    def test_all_records_fail_validation(self):
        """All records fail validation → 200 with all in errors[], nothing created."""
        data = [
            {'full_name': '', 'phone': '111', 'source': 'direct'},       # empty name
            {'full_name': 'B', 'phone': '222', 'source': 'unknown'},     # invalid source
            {'full_name': 'C', 'source': 'direct'},                       # missing phone
        ]
        res = self.client.post(self.url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['created']), 0)
        self.assertEqual(len(res.data['updated']), 0)
        self.assertEqual(len(res.data['errors']), 3)
        self.assertEqual(Professional.objects.count(), 0)


class ListEndpointTests(TestCase):
    """Tests for GET /api/professionals/ — list endpoint.
    Covers DESIGN.md test cases #24–#28."""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/professionals/'

    # #24 — No query param returns all
    def test_no_filter_returns_all(self):
        """GET without filter returns all professionals."""
        Professional.objects.create(full_name='A', phone='111', source='direct')
        Professional.objects.create(full_name='B', phone='222', source='partner')
        Professional.objects.create(full_name='C', phone='333', source='internal')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    # #25 — ?source=direct returns only direct
    def test_source_filter_direct(self):
        """GET ?source=direct returns only direct-source professionals."""
        Professional.objects.create(full_name='A', phone='111', source='direct')
        Professional.objects.create(full_name='B', phone='222', source='partner')
        res = self.client.get(self.url, {'source': 'direct'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['source'], 'direct')

    # #26 — ?source=invalid returns empty list (lenient filter, not a 400)
    def test_source_filter_invalid_value(self):
        """GET ?source=invalid → 200 with empty list (no match, not an error)."""
        Professional.objects.create(full_name='A', phone='111', source='direct')
        res = self.client.get(self.url, {'source': 'invalid'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    # #27 — Empty database
    def test_empty_database(self):
        """GET on empty database returns []."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    # #28 — Ordering is newest first
    def test_ordering_newest_first(self):
        """Results are ordered newest first by created_at."""
        p1 = Professional.objects.create(full_name='First', phone='111', source='direct')
        time.sleep(0.01)  # ensure different timestamps
        p2 = Professional.objects.create(full_name='Second', phone='222', source='direct')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]['full_name'], 'Second')
        self.assertEqual(res.data[1]['full_name'], 'First')
