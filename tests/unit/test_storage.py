"""Unit tests for the storage layer (objects, tree, refs, delta, pack)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vesi.hashing import hash_content
from vesi.storage.objects import ObjectStore
from vesi.storage.tree import Tree, TreeEntry
from vesi.storage.refs import Refs
from vesi.storage.blob import BlobStore
from vesi.storage import delta
from vesi.storage.pack import (
    PackWriter,
    PackReader,
    PackObject,
    ObjectPacker,
)


# ── ObjectStore ────────────────────────────────────────────────────────


class TestObjectStore:
    def test_save_and_load_roundtrip(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_object(b"hello world")
        assert store.load_object(h) == b"hello world"

    def test_hash_is_content_addressed(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_object(b"abc")
        assert h == hash_content(b"abc")

    def test_duplicate_save_returns_same_hash(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h1 = store.save_object(b"abc")
        h2 = store.save_object(b"abc")
        assert h1 == h2
        assert store.count_objects() == 1

    def test_exists(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_object(b"data")
        assert store.exists(h)
        assert not store.exists("deadbeef" * 8)

    def test_load_missing_raises(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        with pytest.raises(FileNotFoundError):
            store.load_object("deadbeef" * 8)

    def test_json_roundtrip(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_json({"nama": "andi", "umur": 20})
        assert store.load_json(h) == {"nama": "andi", "umur": 20}

    def test_empty_content(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_object(b"")
        assert store.load_object(h) == b""

    def test_count_and_size(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        store.save_object(b"aaa")
        store.save_object(b"bbbb")
        assert store.count_objects() == 2
        assert store.total_size() == 7

    def test_verify_integrity_ok(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        store.save_object(b"data")
        assert store.verify_integrity() == []

    def test_verify_integrity_detects_corruption(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        h = store.save_object(b"data")
        obj_file = store._object_path(h)
        obj_file.write_bytes(b"corrupt")
        errors = store.verify_integrity()
        assert errors, "Corruption should be detected"

    def test_large_content_roundtrip(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        data = bytes(range(256)) * 100  # 25600 bytes
        h = store.save_object(data)
        assert store.load_object(h) == data

    def test_binary_content(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        data = b"\x00\x01\x02\xff\xfe"
        h = store.save_object(data)
        assert store.load_object(h) == data


# ── BlobStore ──────────────────────────────────────────────────────────


class TestBlobStore:
    def test_save_and_load_file(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        blobs = BlobStore(store)
        f = tmp_path / "a.txt"
        f.write_bytes(b"isi file")
        h = blobs.save_file(f)
        assert blobs.load_content(h) == b"isi file"

    def test_file_hash_matches_content(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        blobs = BlobStore(store)
        f = tmp_path / "a.txt"
        f.write_bytes(b"isi file")
        assert blobs.file_hash(f) == hash_content(b"isi file")

    def test_file_hash_does_not_save(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        blobs = BlobStore(store)
        f = tmp_path / "a.txt"
        f.write_bytes(b"isi file")
        blobs.file_hash(f)
        assert store.count_objects() == 0


# ── Tree ───────────────────────────────────────────────────────────────


class TestTree:
    def test_add_and_get_entry(self):
        tree = Tree()
        tree.add_blob("a.txt", "hash123", "a.txt")
        assert tree.get_entry("a.txt").name == "a.txt"

    def test_get_entry_missing_returns_none(self):
        tree = Tree()
        assert tree.get_entry("tak-ada") is None

    def test_get_blob_entries_filters_types(self):
        tree = Tree()
        tree.add_blob("a.txt", "h1", "a.txt")
        tree.add_tree("subdir", "t1", "subdir")
        blob_entries = tree.get_blob_entries()
        assert len(blob_entries) == 1
        assert blob_entries[0].path == "a.txt"

    def test_to_dict_roundtrip(self):
        tree = Tree()
        tree.add_blob("a.txt", "h1", "a.txt")
        tree.add_tree("subdir", "t1", "subdir")
        restored = Tree.from_dict(tree.to_dict())
        assert restored.get_entry("a.txt").hash_id == "h1"
        assert restored.get_entry("subdir").type == "tree"

    def test_save_and_load_via_objects(self, tmp_path):
        store = ObjectStore(tmp_path / "objects")
        tree = Tree()
        tree.add_blob("a.txt", "h1", "a.txt")
        h = tree.save(store)
        loaded = Tree.load(store, h)
        assert loaded.get_entry("a.txt").hash_id == "h1"


# ── Refs ───────────────────────────────────────────────────────────────


class TestRefs:
    def test_init_creates_default_branch(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        refs.init("utama")
        assert refs.get_active_branch() == "utama"
        assert refs.list_branches() == ["utama"]

    def test_set_and_get_branch_hash(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        refs.init("utama")
        refs.set_branch_hash("utama", "abc1234")
        assert refs.get_branch_hash("utama") == "abc1234"

    def test_set_head_detached(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        refs.set_head("0123456789abcdef")
        assert refs.get_head() == "0123456789abcdef"
        assert refs.get_active_branch() is None

    def test_set_head_branch(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        refs.set_head("fitur-x")
        assert refs.get_head() == "fitur-x"
        assert refs.get_active_branch() == "fitur-x"

    def test_delete_branch(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        refs.init("utama")
        refs.set_branch_hash("lain", "deadbeef")
        assert refs.delete_branch("lain") is True
        assert refs.delete_branch("lain") is False
        assert refs.list_branches() == ["utama"]

    def test_get_head_without_file_returns_none(self, tmp_path):
        refs = Refs(tmp_path / "refs")
        assert refs.get_head() is None


# ── Delta ──────────────────────────────────────────────────────────────


class TestDelta:
    def test_identical_content(self):
        base = b"abcdefgh" * 10
        d = delta.create_delta(base, base)
        assert delta.apply_delta(base, d) == base

    def test_empty_base(self):
        d = delta.create_delta(b"", b"hello")
        assert delta.apply_delta(b"", d) == b"hello"

    def test_empty_target(self):
        assert delta.apply_delta(b"base", delta.create_delta(b"base", b"")) == b""

    def test_small_change(self):
        base = b"the quick brown fox"
        target = b"the quick brown cat"
        d = delta.create_delta(base, target)
        assert delta.apply_delta(base, d) == target

    def test_appended_content(self):
        base = b"line1\n"
        target = b"line1\nline2\n"
        d = delta.create_delta(base, target)
        assert delta.apply_delta(base, d) == target

    def test_binary_changes(self):
        base = bytes(range(100))
        target = bytes(range(1, 101))  # shifted
        d = delta.create_delta(base, target)
        assert delta.apply_delta(base, d) == target

    def test_base_size_mismatch_raises(self):
        with pytest.raises(ValueError):
            delta.apply_delta(b"wrong", delta.create_delta(b"base", b"target"))

    def test_compress_smaller_than_target(self):
        compressor = delta.DeltaCompressor()
        base = b"the quick brown fox jumps"
        target = b"the quick brown fox jumps again"
        data, was_delta = compressor.compress_pair(base, target)
        assert compressor.decompress(base, data, was_delta) == target

    def test_encode_decode_size_roundtrip(self):
        for size in [0, 1, 127, 128, 255, 256, 16384, 1048576]:
            encoded = delta._encode_size(size)
            decoded, pos = delta._decode_size(encoded, 0)
            assert decoded == size
            assert pos == len(encoded)


# ── Pack ───────────────────────────────────────────────────────────────


class TestPack:
    def test_write_and_read_roundtrip(self, tmp_path):
        packs_dir = tmp_path / "packs"
        writer = PackWriter(packs_dir)
        objects = [
            PackObject(obj_type=1, data=b"first object"),
            PackObject(obj_type=2, data=b'{"entries": []}'),
            PackObject(obj_type=3, data=b'{"message": "hi", "tree": "x"}'),
        ]
        pack_path = writer.create_pack(objects)

        reader = PackReader(pack_path)
        for obj in objects:
            assert reader.has_object(obj.hash_id)
            loaded = reader.read_object(obj.hash_id)
            assert loaded.data == obj.data
            assert loaded.obj_type == obj.obj_type

    def test_pack_info(self, tmp_path):
        packs_dir = tmp_path / "packs"
        writer = PackWriter(packs_dir)
        obj = PackObject(obj_type=1, data=b"data")
        pack_path = writer.create_pack([obj])
        info = PackReader(pack_path).pack_info()
        assert info["objects"] == 1
        assert info["size_bytes"] == pack_path.stat().st_size
        assert "B" in info["size_human"] or "KB" in info["size_human"]

    def test_list_objects(self, tmp_path):
        packs_dir = tmp_path / "packs"
        writer = PackWriter(packs_dir)
        objs = [PackObject(obj_type=1, data=b"a"), PackObject(obj_type=1, data=b"b")]
        pack_path = writer.create_pack(objs)
        assert set(PackReader(pack_path).list_objects()) == {o.hash_id for o in objs}

    def test_empty_pack_roundtrip(self, tmp_path):
        packs_dir = tmp_path / "packs"
        writer = PackWriter(packs_dir)
        pack_path = writer.create_pack([])
        reader = PackReader(pack_path)
        assert reader.list_objects() == []

    def test_missing_object_returns_none(self, tmp_path):
        packs_dir = tmp_path / "packs"
        writer = PackWriter(packs_dir)
        writer.create_pack([PackObject(obj_type=1, data=b"a")])
        reader = PackReader(writer._current_pack)
        assert reader.read_object("deadbeef" * 8) is None


class TestObjectPacker:
    def test_find_object_loose(self, tmp_path):
        objects_dir = tmp_path / "objects"
        packs_dir = tmp_path / "packs"
        store = ObjectStore(objects_dir)
        h = store.save_object(b"loose data")
        packer = ObjectPacker(objects_dir, packs_dir)
        assert packer.has_object(h)
        assert packer.find_object(h) == b"loose data"

    def test_find_object_missing(self, tmp_path):
        packer = ObjectPacker(tmp_path / "objects", tmp_path / "packs")
        assert packer.find_object("deadbeef" * 8) is None
        assert packer.has_object("deadbeef" * 8) is False

    def test_pack_stats(self, tmp_path):
        objects_dir = tmp_path / "objects"
        packs_dir = tmp_path / "packs"
        store = ObjectStore(objects_dir)
        store.save_object(b"some data")
        packer = ObjectPacker(objects_dir, packs_dir)
        stats = packer.pack_stats()
        assert stats["loose_objects"] == 1
        assert stats["packs"] == 0

    def test_detect_type(self, tmp_path):
        packer = ObjectPacker(tmp_path / "objects", tmp_path / "packs")
        assert packer._detect_type(b'{"tree": "x", "message": "m"}') == 3
        assert packer._detect_type(b'{"entries": []}') == 2
        assert packer._detect_type(b"plain bytes") == 1