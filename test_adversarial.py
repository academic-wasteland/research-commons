import pytest
from research_commons.schema import _FORMAT_CHECKER, validate_against
from jsonschema import Draft202012Validator
from research_commons.ro_crate import _derive_action_id, build_crate, unpack_and_verify_crate

def test_derive_action_id_empty_msg_id():
    import hashlib
    from research_commons.ro_crate import _derive_action_id
    expected = f"#action-{hashlib.sha256(b'').hexdigest()[:12]}"
    assert _derive_action_id("") == expected
    assert _derive_action_id(None) == expected

test_derive_action_id_empty_msg_id()
print("test_derive_action_id_empty_msg_id passed")
