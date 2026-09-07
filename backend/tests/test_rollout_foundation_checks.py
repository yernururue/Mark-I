"""Regression coverage for metadata-only rollout foundation gates."""

import copy
import json
from pathlib import Path
import unittest

from scripts.rollout_foundation_checks import (
    evaluate_enabled_apis,
    evaluate_indexes,
    evaluate_project_metadata,
    evaluate_protected_file,
    evaluate_secret_versions,
)


INDEXES = json.loads((Path(__file__).resolve().parents[1] / "firestore.indexes.json").read_text())["indexes"]


def live_index(declaration, state="READY", number=1):
    index = copy.deepcopy(declaration)
    collection = index.pop("collectionGroup")
    index["name"] = f"projects/test/databases/mark-i/collectionGroups/{collection}/indexes/{number}"
    index["state"] = state
    index["fields"].append({"fieldPath": "__name__", "order": "DESCENDING"})
    return index


def version(number, state):
    return {"name": f"projects/test/secrets/example/versions/{number}", "state": state}


class IndexReadinessTests(unittest.TestCase):
    def test_all_declared_indexes_match_live_resource_names_and_implicit_name(self):
        live = [live_index(index, number=i) for i, index in enumerate(INDEXES, 1)]
        self.assertEqual([row["state"] for row in evaluate_indexes(INDEXES, live)], ["READY"] * len(INDEXES))

    def test_four_unrelated_ready_indexes_do_not_pass(self):
        live = [live_index(INDEXES[-1], number=i) for i in range(4)]
        self.assertEqual([row["state"] for row in evaluate_indexes(INDEXES, live)], ["MISSING"] * 3 + ["READY"])

    def test_order_scope_collection_and_direction_are_significant(self):
        for mutation in ("field-order", "scope", "collection", "direction"):
            with self.subTest(mutation=mutation):
                live = live_index(INDEXES[0])
                if mutation == "field-order":
                    live["fields"][0], live["fields"][1] = live["fields"][1], live["fields"][0]
                elif mutation == "scope":
                    live["queryScope"] = "COLLECTION_GROUP"
                elif mutation == "collection":
                    live["name"] = live["name"].replace("/observations/", "/messages/")
                else:
                    live["fields"][0]["order"] = "DESCENDING"
                self.assertEqual(evaluate_indexes([INDEXES[0]], [live])[0]["state"], "MISSING")

    def test_incomplete_and_error_states_are_reported(self):
        for state in ("CREATING", "NEEDS_REPAIR", "ERROR", "UNKNOWN"):
            with self.subTest(state=state):
                self.assertEqual(evaluate_indexes([INDEXES[0]], [live_index(INDEXES[0], state)])[0]["state"], state)

    def test_extra_ready_and_creating_indexes_do_not_hide_missing_declaration(self):
        live = [live_index(INDEXES[0]), live_index(INDEXES[1], "CREATING")]
        self.assertEqual([row["state"] for row in evaluate_indexes(INDEXES, live)], ["READY", "CREATING", "MISSING", "MISSING"])

    def test_explicit_document_name_order_is_respected(self):
        expected = copy.deepcopy(INDEXES[0])
        expected["fields"].append({"fieldPath": "__name__", "order": "ASCENDING"})
        self.assertEqual(evaluate_indexes([expected], [live_index(INDEXES[0])])[0]["state"], "MISSING")

    def test_malformed_metadata_cannot_satisfy_index(self):
        malformed = live_index(INDEXES[0])
        malformed["collectionGroup"] = "wrong"
        self.assertEqual(evaluate_indexes([INDEXES[0]], [None, {}, malformed])[0]["state"], "MISSING")
        with self.assertRaises(ValueError):
            evaluate_indexes([], [])


class SecretReadinessTests(unittest.TestCase):
    def test_resource_without_enabled_versions_is_not_ready(self):
        self.assertEqual(evaluate_secret_versions([])["state"], "MISSING")
        self.assertEqual(evaluate_secret_versions([version(1, "DISABLED")])["state"], "DISABLED")
        self.assertEqual(evaluate_secret_versions([version(1, "DESTROYED")])["state"], "DESTROYED")

    def test_any_enabled_version_is_sufficient_without_pin(self):
        result = evaluate_secret_versions([version(2, "ENABLED"), version(10, "DISABLED"), version(1, "ENABLED")])
        self.assertEqual(result, {"state": "ENABLED", "version": "2", "enabled_versions": ["1", "2"]})

    def test_pin_must_itself_be_enabled(self):
        versions = [version(1, "DISABLED"), version(2, "ENABLED")]
        self.assertEqual(evaluate_secret_versions(versions, "1")["state"], "DISABLED")
        self.assertEqual(evaluate_secret_versions(versions, "2")["state"], "ENABLED")
        self.assertEqual(evaluate_secret_versions(versions, "3")["state"], "MISSING")
        self.assertEqual(evaluate_secret_versions(versions, version(2, "ENABLED")["name"])["state"], "ENABLED")

    def test_latest_does_not_fall_back_to_older_enabled_version(self):
        versions = [version(2, "ENABLED"), version(10, "DESTROYED")]
        result = evaluate_secret_versions(versions, "latest")
        self.assertEqual((result["state"], result["version"]), ("DESTROYED", "10"))

    def test_malformed_or_conflicting_versions_fail_closed(self):
        versions = [None, {}, version("latest", "ENABLED"), version(1, "ENABLED"), version(1, "DISABLED")]
        self.assertEqual(evaluate_secret_versions(versions)["state"], "UNKNOWN")
        with self.assertRaises(ValueError):
            evaluate_secret_versions([], "garbage")


class ProtectedFileTests(unittest.TestCase):
    def test_regular_file_requires_exact_0600_mode(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            path = Path(directory, "credential")
            path.write_text("never-read", encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(evaluate_protected_file(path), {"state": "READY", "mode": "0600"})
            path.chmod(0o640)
            self.assertEqual(evaluate_protected_file(path), {"state": "INSECURE_MODE", "mode": "0640"})

    def test_unset_missing_directory_and_symlink_fail_closed(self):
        from tempfile import TemporaryDirectory

        self.assertEqual(evaluate_protected_file(None), {"state": "UNSET"})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(evaluate_protected_file(root / "missing"), {"state": "MISSING"})
            self.assertEqual(evaluate_protected_file(root), {"state": "NOT_REGULAR"})
            target = root / "target"
            target.write_text("never-read", encoding="utf-8")
            link = root / "link"
            link.symlink_to(target)
            self.assertEqual(evaluate_protected_file(link), {"state": "SYMLINK"})


class ProjectFoundationTests(unittest.TestCase):
    def test_project_identity_requires_exact_active_project(self):
        metadata = {"projectId": "mark-i-506218", "projectNumber": "691051892786", "lifecycleState": "ACTIVE"}
        self.assertEqual(
            evaluate_project_metadata(metadata, project_id="mark-i-506218", project_number="691051892786")["state"],
            "READY",
        )
        for key, value in (("projectId", "wrong"), ("projectNumber", "1"), ("lifecycleState", "DELETE_REQUESTED")):
            with self.subTest(key=key):
                changed = {**metadata, key: value}
                self.assertNotEqual(
                    evaluate_project_metadata(changed, project_id="mark-i-506218", project_number="691051892786")["state"],
                    "READY",
                )

    def test_required_apis_are_compared_by_canonical_name(self):
        required = ("run.googleapis.com", "pubsub.googleapis.com")
        live = [{"config": {"name": "run.googleapis.com"}}]
        self.assertEqual(evaluate_enabled_apis(live, required), {"state": "MISSING", "missing": ["pubsub.googleapis.com"]})
        live.append({"config": {"name": "pubsub.googleapis.com"}})
        self.assertEqual(evaluate_enabled_apis(live, required), {"state": "READY", "missing": []})
        self.assertEqual(evaluate_enabled_apis({}, required)["state"], "INVALID")


if __name__ == "__main__":
    unittest.main()
