"""Tests for Git import/export bridge."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import zlib
from pathlib import Path

import pytest

from vesi.core.git_parser import GitParser, GitObject, GitBlob, GitTree, GitCommit, GitTreeEntry
from vesi.core.git_writer import GitWriter


# ═══════════════════════════════════════════════════════════════════
# GIT PARSER TESTS
# ═══════════════════════════════════════════════════════════════════


class TestGitParser:
    """Test Git object parser."""

    def setup_method(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.git_dir = self.tmp_dir / ".git"
        self.git_dir.mkdir(parents=True)
        (self.git_dir / "objects").mkdir()
        (self.git_dir / "refs" / "heads").mkdir(parents=True)
        (self.git_dir / "refs" / "tags").mkdir(parents=True)

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    def _write_loose_object(self, hash_id: str, data: bytes) -> None:
        """Write a loose Git object."""
        obj_dir = self.git_dir / "objects" / hash_id[:2]
        obj_dir.mkdir(parents=True, exist_ok=True)
        compressed = zlib.compress(data)
        (obj_dir / hash_id[2:]).write_bytes(compressed)

    def test_has_git_repo_true(self):
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        parser = GitParser(self.git_dir)
        assert parser.has_git_repo() is True

    def test_has_git_repo_false(self):
        parser = GitParser(self.tmp_dir / "nonexistent")
        assert parser.has_git_repo() is False

    def test_read_loose_blob(self):
        content = b"Hello, World!"
        header = f"blob {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_loose_object(hash_id, store)

        parser = GitParser(self.git_dir)
        obj = parser.read_object(hash_id)

        assert obj is not None
        assert obj.obj_type == "blob"
        assert obj.data == content
        assert obj.hash_id == hash_id

    def test_read_loose_commit(self):
        content = b"tree abc123\nauthor Test <test@test.com> 1234567890 +0000\n\nInitial commit"
        header = f"commit {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_loose_object(hash_id, store)

        parser = GitParser(self.git_dir)
        obj = parser.read_object(hash_id)

        assert obj is not None
        assert obj.obj_type == "commit"

    def test_parse_blob(self):
        content = b"File content here"
        header = f"blob {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        git_obj = GitObject(obj_type="blob", data=content, hash_id=hash_id)
        parser = GitParser(self.git_dir)
        blob = parser.parse_blob(git_obj)

        assert blob.content == content
        assert blob.hash_id == hash_id

    def test_parse_tree(self):
        # Create tree content: mode name\0hash (20 bytes)
        entries = []

        # Entry 1: file.txt with mode 100644
        name1 = b"file.txt"
        hash1 = bytes.fromhex("a" * 40)
        entries.append(f"100644 file.txt\x00".encode() + hash1)

        # Entry 2: subdir with mode 040000
        name2 = b"subdir"
        hash2 = bytes.fromhex("b" * 40)
        entries.append(f"040000 subdir\x00".encode() + hash2)

        tree_data = b"".join(entries)
        header = f"tree {len(tree_data)}\x00".encode()
        store = header + tree_data
        hash_id = hashlib.sha1(store).hexdigest()

        git_obj = GitObject(obj_type="tree", data=tree_data, hash_id=hash_id)
        parser = GitParser(self.git_dir)
        tree = parser.parse_tree(git_obj)

        assert len(tree.entries) == 2
        assert tree.entries[0].name == "file.txt"
        assert tree.entries[0].mode == 100644
        assert tree.entries[0].is_blob is True
        assert tree.entries[1].name == "subdir"
        assert tree.entries[1].mode == 40000  # Git stores as decimal string "40000"
        assert tree.entries[1].is_tree is True

    def test_parse_commit(self):
        tree_hash = "a" * 40
        parent1 = "b" * 40
        parent2 = "c" * 40

        content = f"""tree {tree_hash}
parent {parent1}
parent {parent2}
author John Doe <john@example.com> 1234567890 +0000
committer John Doe <john@example.com> 1234567900 +0000

Merge commit message"""
        content_bytes = content.encode("utf-8")
        header = f"commit {len(content_bytes)}\x00".encode()
        store = header + content_bytes
        hash_id = hashlib.sha1(store).hexdigest()

        git_obj = GitObject(obj_type="commit", data=content_bytes, hash_id=hash_id)
        parser = GitParser(self.git_dir)
        commit = parser.parse_commit(git_obj)

        assert commit.tree_hash == tree_hash
        assert len(commit.parent_hashes) == 2
        assert commit.parent_hashes[0] == parent1
        assert commit.parent_hashes[1] == parent2
        assert commit.author == "John Doe"
        assert commit.author_email == "john@example.com"
        assert commit.message == "Merge commit message"
        assert commit.is_merge is True

    def test_parse_simple_commit(self):
        tree_hash = "a" * 40
        content = f"""tree {tree_hash}
author Jane <jane@test.com> 1234567890 +0000

Simple commit"""
        content_bytes = content.encode("utf-8")
        header = f"commit {len(content_bytes)}\x00".encode()
        store = header + content_bytes
        hash_id = hashlib.sha1(store).hexdigest()

        git_obj = GitObject(obj_type="commit", data=content_bytes, hash_id=hash_id)
        parser = GitParser(self.git_dir)
        commit = parser.parse_commit(git_obj)

        assert commit.tree_hash == tree_hash
        assert len(commit.parent_hashes) == 0
        assert commit.is_merge is False

    def test_read_refs_branches(self):
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (self.git_dir / "refs" / "heads" / "main").write_text("abc123\n")
        (self.git_dir / "refs" / "heads" / "feature").write_text("def456\n")

        parser = GitParser(self.git_dir)
        refs = parser.read_refs()

        head_refs = [r for r in refs if r.name == "HEAD"]
        assert len(head_refs) == 1
        assert head_refs[0].ref_type == "symbolic"
        assert head_refs[0].target == "refs/heads/main"

        branch_refs = [r for r in refs if r.ref_type == "branch"]
        assert len(branch_refs) == 2
        branch_names = [r.name for r in branch_refs]
        assert "main" in branch_names
        assert "feature" in branch_names

    def test_read_refs_tags(self):
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (self.git_dir / "refs" / "tags" / "v1.0").write_text("aaa111\n")

        parser = GitParser(self.git_dir)
        refs = parser.read_refs()

        tag_refs = [r for r in refs if r.ref_type == "tag"]
        assert len(tag_refs) == 1
        assert tag_refs[0].name == "v1.0"

    def test_resolve_head_symbolic(self):
        (self.git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (self.git_dir / "refs" / "heads" / "main").write_text("abc123def456\n")

        parser = GitParser(self.git_dir)
        head = parser.resolve_head()

        assert head == "abc123def456"

    def test_resolve_head_detached(self):
        (self.git_dir / "HEAD").write_text("abc123def456789\n")

        parser = GitParser(self.git_dir)
        head = parser.resolve_head()

        assert head == "abc123def456789"

    def test_read_nonexistent_object(self):
        parser = GitParser(self.git_dir)
        obj = parser.read_object("0" * 40)
        assert obj is None


# ═══════════════════════════════════════════════════════════════════
# GIT WRITER TESTS
# ═══════════════════════════════════════════════════════════════════


class TestGitWriter:
    """Test Git object writer."""

    def setup_method(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.git_dir = self.tmp_dir / ".git"

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    def test_init_creates_directories(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        assert (self.git_dir / "objects").is_dir()
        assert (self.git_dir / "refs" / "heads").is_dir()
        assert (self.git_dir / "refs" / "tags").is_dir()
        assert (self.git_dir / "info").is_dir()
        assert (self.git_dir / "hooks").is_dir()

    def test_write_blob(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        content = b"Hello, Git!"
        hash_id = writer.write_blob(content)

        # Verify hash
        header = f"blob {len(content)}\x00".encode()
        store = header + content
        expected_hash = hashlib.sha1(store).hexdigest()
        assert hash_id == expected_hash

        # Verify file exists
        obj_path = self.git_dir / "objects" / hash_id[:2] / hash_id[2:]
        assert obj_path.is_file()

    def test_write_blob_returns_same_hash(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        content = b"Same content"
        hash1 = writer.write_blob(content)
        hash2 = writer.write_blob(content)

        assert hash1 == hash2

    def test_write_tree(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        entries = [
            ("file.txt", 100644, "a" * 40),
            ("script.py", 100755, "b" * 40),
        ]

        hash_id = writer.write_tree(entries)
        assert len(hash_id) == 40

    def test_write_commit(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        tree_hash = "a" * 40
        hash_id = writer.write_commit(
            tree_hash=tree_hash,
            author="Test User",
            author_email="test@example.com",
            author_timestamp=1234567890,
            message="Test commit",
        )

        assert len(hash_id) == 40

    def test_write_commit_with_parents(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        parent1 = "b" * 40
        parent2 = "c" * 40

        hash_id = writer.write_commit(
            tree_hash="a" * 40,
            parent_hashes=[parent1, parent2],
            author="Test User",
            author_email="test@example.com",
            message="Merge commit",
        )

        assert len(hash_id) == 40

    def test_write_tag(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        target_hash = "a" * 40
        hash_id = writer.write_tag(
            tag_name="v1.0",
            target_hash=target_hash,
            tagger="Test User",
            tagger_email="test@example.com",
            message="Release v1.0",
        )

        assert len(hash_id) == 40

    def test_set_head_symbolic(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        writer.set_head("main", symbolic=True)

        head_content = (self.git_dir / "HEAD").read_text()
        assert head_content == "ref: refs/heads/main\n"

    def test_set_head_detached(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        hash_id = "a" * 40
        writer.set_head(hash_id, symbolic=False)

        head_content = (self.git_dir / "HEAD").read_text()
        assert head_content == f"{hash_id}\n"

    def test_set_branch(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        hash_id = "a" * 40
        writer.set_branch("main", hash_id)

        branch_file = self.git_dir / "refs" / "heads" / "main"
        assert branch_file.is_file()
        assert branch_file.read_text().strip() == hash_id

    def test_set_tag(self):
        writer = GitWriter(self.git_dir)
        writer.init()

        hash_id = "a" * 40
        writer.set_tag("v1.0", hash_id)

        tag_file = self.git_dir / "refs" / "tags" / "v1.0"
        assert tag_file.is_file()
        assert tag_file.read_text().strip() == hash_id

    def test_write_config(self):
        writer = GitWriter(self.git_dir)
        writer.init()
        writer.write_config(bare=False)

        config_file = self.git_dir / "config"
        assert config_file.is_file()
        content = config_file.read_text()
        assert "repositoryformatversion = 0" in content
        assert "bare = false" in content

    def test_write_config_bare(self):
        writer = GitWriter(self.git_dir)
        writer.init()
        writer.write_config(bare=True)

        config_file = self.git_dir / "config"
        content = config_file.read_text()
        assert "bare = true" in content


# ═══════════════════════════════════════════════════════════════════
# GIT IMPORT/EXPORT COMMAND TESTS
# ═══════════════════════════════════════════════════════════════════


class TestGitImportExport:
    """Test Git import/export commands."""

    def setup_method(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.original_dir = os.getcwd()

    def teardown_method(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.tmp_dir)

    def test_git_parser_import_in_vesi(self):
        """Test that git_parser can be imported and used."""
        from vesi.core.git_parser import GitParser

        git_dir = self.tmp_dir / ".git"
        git_dir.mkdir(parents=True)
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

        parser = GitParser(git_dir)
        assert parser.has_git_repo() is True

    def test_git_writer_import_in_vesi(self):
        """Test that git_writer can be imported and used."""
        from vesi.core.git_writer import GitWriter

        git_dir = self.tmp_dir / ".git"
        writer = GitWriter(git_dir)
        writer.init()

        assert (git_dir / "objects").is_dir()

    def test_roundtrip_blob(self):
        """Test writing and reading a blob."""
        writer = GitWriter(self.tmp_dir / ".git_out")
        writer.init()

        content = b"Test content for roundtrip"
        hash_id = writer.write_blob(content)

        parser = GitParser(self.tmp_dir / ".git_out")
        obj = parser.read_object(hash_id)

        assert obj is not None
        assert obj.obj_type == "blob"
        assert obj.data == content

    def test_roundtrip_tree(self):
        """Test writing and reading a tree."""
        writer = GitWriter(self.tmp_dir / ".git_out")
        writer.init()

        # Write a blob first
        blob_content = b"file content"
        blob_hash = writer.write_blob(blob_content)

        # Write tree referencing the blob
        entries = [("test.txt", 100644, blob_hash)]
        tree_hash = writer.write_tree(entries)

        # Read it back
        parser = GitParser(self.tmp_dir / ".git_out")
        obj = parser.read_object(tree_hash)

        assert obj is not None
        assert obj.obj_type == "tree"

        tree = parser.parse_tree(obj)
        assert len(tree.entries) == 1
        assert tree.entries[0].name == "test.txt"
        assert tree.entries[0].hash_id == blob_hash

    def test_roundtrip_commit(self):
        """Test writing and reading a commit."""
        writer = GitWriter(self.tmp_dir / ".git_out")
        writer.init()

        # Write tree
        tree_hash = writer.write_tree([])

        # Write commit
        commit_hash = writer.write_commit(
            tree_hash=tree_hash,
            author="Test",
            author_email="test@test.com",
            message="Test commit",
        )

        # Read it back
        parser = GitParser(self.tmp_dir / ".git_out")
        obj = parser.read_object(commit_hash)

        assert obj is not None
        assert obj.obj_type == "commit"

        commit = parser.parse_commit(obj)
        assert commit.tree_hash == tree_hash
        assert commit.author == "Test"
        assert commit.message == "Test commit"

    def test_roundtrip_with_parents(self):
        """Test commit with parent chain."""
        writer = GitWriter(self.tmp_dir / ".git_out")
        writer.init()

        tree_hash = writer.write_tree([])

        # First commit
        commit1 = writer.write_commit(
            tree_hash=tree_hash,
            author="Author",
            author_email="author@test.com",
            message="First commit",
        )

        # Second commit with parent
        commit2 = writer.write_commit(
            tree_hash=tree_hash,
            parent_hashes=[commit1],
            author="Author",
            author_email="author@test.com",
            message="Second commit",
        )

        # Read second commit
        parser = GitParser(self.tmp_dir / ".git_out")
        obj = parser.read_object(commit2)
        commit = parser.parse_commit(obj)

        assert len(commit.parent_hashes) == 1
        assert commit.parent_hashes[0] == commit1

    def test_refs_workflow(self):
        """Test creating and reading refs."""
        writer = GitWriter(self.tmp_dir / ".git_out")
        writer.init()

        # Create commits
        tree_hash = writer.write_tree([])
        commit_hash = writer.write_commit(
            tree_hash=tree_hash,
            author="Author",
            author_email="author@test.com",
            message="Commit",
        )

        # Set branches
        writer.set_branch("main", commit_hash)
        writer.set_branch("feature", commit_hash)

        # Set HEAD
        writer.set_head("main", symbolic=True)

        # Read back
        parser = GitParser(self.tmp_dir / ".git_out")
        refs = parser.read_refs()

        branches = [r for r in refs if r.ref_type == "branch"]
        assert len(branches) == 2

        head = [r for r in refs if r.name == "HEAD"][0]
        assert head.ref_type == "symbolic"
        assert head.target == "refs/heads/main"
