import hashlib
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.test import override_settings

from documents.tests.utils import DirectoriesMixin, TestMigrations


STORAGE_TYPE_GPG = "gpg"


def archive_name_from_filename(filename):
    return os.path.splitext(filename)[0] + ".pdf"


def archive_path_old(self):
    if self.filename:
        fname = archive_name_from_filename(self.filename)
    else:
        fname = "{:07}.pdf".format(self.pk)

    return os.path.join(
        settings.ARCHIVE_DIR,
        fname
    )


def archive_path_new(doc):
        if doc.archive_filename is not None:
            return os.path.join(
                settings.ARCHIVE_DIR,
                str(doc.archive_filename)
            )
        else:
            return None


def source_path(doc):
    if doc.filename:
        fname = str(doc.filename)
    else:
        fname = "{:07}{}".format(doc.pk, doc.file_type)
        if doc.storage_type == STORAGE_TYPE_GPG:
            fname += ".gpg"  # pragma: no cover

    return os.path.join(
        settings.ORIGINALS_DIR,
        fname
    )


def thumbnail_path(doc):
    file_name = "{:07}.png".format(doc.pk)
    if doc.storage_type == STORAGE_TYPE_GPG:
        file_name += ".gpg"

    return os.path.join(
        settings.THUMBNAIL_DIR,
        file_name
    )


def make_test_document(document_class, title: str, mime_type: str, original: str, original_filename: str, archive: str = None, archive_filename: str = None):
    doc = document_class()
    doc.filename = original_filename
    doc.title = title
    doc.mime_type = mime_type
    doc.content = "the content, does not matter for this test"
    doc.save()

    shutil.copy2(original, source_path(doc))
    with open(original, "rb") as f:
        doc.checksum = hashlib.md5(f.read()).hexdigest()

    if archive:
        if archive_filename:
            doc.archive_filename = archive_filename
            shutil.copy2(archive, archive_path_new(doc))
        else:
            shutil.copy2(archive, archive_path_old(doc))

        with open(archive, "rb") as f:
            doc.archive_checksum = hashlib.md5(f.read()).hexdigest()

    doc.save()

    Path(thumbnail_path(doc)).touch()

    return doc


simple_jpg = os.path.join(os.path.dirname(__file__), "samples", "simple.jpg")
simple_pdf = os.path.join(os.path.dirname(__file__), "samples", "simple.pdf")
simple_pdf2 = os.path.join(os.path.dirname(__file__), "samples", "documents", "originals", "0000002.pdf")
simple_txt = os.path.join(os.path.dirname(__file__), "samples", "simple.txt")
simple_png = os.path.join(os.path.dirname(__file__), "samples", "simple-noalpha.png")


@override_settings(PAPERLESS_FILENAME_FORMAT="")
class TestMigrateArchiveFiles(DirectoriesMixin, TestMigrations):

    migrate_from = '1011_auto_20210101_2340'
    migrate_to = '1012_fix_archive_files'

    def setUpBeforeMigration(self, apps):
        Document = apps.get_model("documents", "Document")

        doc_no_archive = make_test_document(Document, "no_archive", "text/plain", simple_txt, "no_archive.txt")
        clash1 = make_test_document(Document, "clash", "application/pdf", simple_pdf, "clash.pdf", simple_pdf)
        clash2 = make_test_document(Document, "clash", "image/jpeg", simple_jpg, "clash.jpg", simple_pdf)
        clash3 = make_test_document(Document, "clash", "image/png", simple_png, "clash.png", simple_pdf)
        clash4 = make_test_document(Document, "clash.png", "application/pdf", simple_pdf2, "clash.png.pdf", simple_pdf2)

        self.assertEqual(archive_path_old(clash1), archive_path_old(clash2))
        self.assertEqual(archive_path_old(clash1), archive_path_old(clash3))
        self.assertNotEqual(archive_path_old(clash1), archive_path_old(clash4))

    def testArchiveFilesMigrated(self):
        Document = self.apps.get_model('documents', 'Document')

        for doc in Document.objects.all():
            if doc.archive_checksum:
                self.assertIsNotNone(doc.archive_filename)
                self.assertTrue(os.path.isfile(archive_path_new(doc)))
            else:
                self.assertIsNone(doc.archive_filename)

            with open(source_path(doc), "rb") as f:
                original_checksum = hashlib.md5(f.read()).hexdigest()
            self.assertEqual(original_checksum, doc.checksum)

            if doc.archive_checksum:
                self.assertTrue(os.path.isfile(archive_path_new(doc)))
                with open(archive_path_new(doc), "rb") as f:
                    archive_checksum = hashlib.md5(f.read()).hexdigest()
                self.assertEqual(archive_checksum, doc.archive_checksum)

        self.assertEqual(Document.objects.filter(archive_checksum__isnull=False).count(), 4)


@override_settings(PAPERLESS_FILENAME_FORMAT="{correspondent}/{title}")
class TestMigrateArchiveFilesWithFilenameFormat(TestMigrateArchiveFiles):
    pass


@override_settings(PAPERLESS_FILENAME_FORMAT="")
class TestMigrateArchiveFilesBackwards(DirectoriesMixin, TestMigrations):

    migrate_from = '1012_fix_archive_files'
    migrate_to = '1011_auto_20210101_2340'

    def setUpBeforeMigration(self, apps):

        Document = apps.get_model("documents", "Document")

        doc_unrelated = make_test_document(Document, "unrelated", "application/pdf", simple_pdf2, "unrelated.txt", simple_pdf2, "unrelated.pdf")
        doc_no_archive = make_test_document(Document, "no_archive", "text/plain", simple_txt, "no_archive.txt")
        clashB = make_test_document(Document, "clash", "image/jpeg", simple_jpg, "clash.jpg", simple_pdf, "clash_02.pdf")

    def testArchiveFilesReverted(self):
        Document = self.apps.get_model('documents', 'Document')

        for doc in Document.objects.all():
            if doc.archive_checksum:
                self.assertTrue(os.path.isfile(archive_path_old(doc)))
            with open(source_path(doc), "rb") as f:
                original_checksum = hashlib.md5(f.read()).hexdigest()
            self.assertEqual(original_checksum, doc.checksum)

            if doc.archive_checksum:
                self.assertTrue(os.path.isfile(archive_path_old(doc)))
                with open(archive_path_old(doc), "rb") as f:
                    archive_checksum = hashlib.md5(f.read()).hexdigest()
                self.assertEqual(archive_checksum, doc.archive_checksum)

        self.assertEqual(Document.objects.filter(archive_checksum__isnull=False).count(), 2)


@override_settings(PAPERLESS_FILENAME_FORMAT="{correspondent}/{title}")
class TestMigrateArchiveFilesBackwardsWithFilenameFormat(TestMigrateArchiveFilesBackwards):
    pass


@override_settings(PAPERLESS_FILENAME_FORMAT="")
class TestMigrateArchiveFilesBackwardsErrors(DirectoriesMixin, TestMigrations):

    migrate_from = '1012_fix_archive_files'
    migrate_to = '1011_auto_20210101_2340'
    auto_migrate = False

    def test_filename_clash(self):

        Document = self.apps.get_model("documents", "Document")

        self.clashA = make_test_document(Document, "clash", "application/pdf", simple_pdf, "clash.pdf", simple_pdf, "clash_02.pdf")
        self.clashB = make_test_document(Document, "clash", "image/jpeg", simple_jpg, "clash.jpg", simple_pdf, "clash_01.pdf")

        self.assertRaisesMessage(ValueError, "would clash with another archive filename", self.performMigration)

    def test_filename_exists(self):

        Document = self.apps.get_model("documents", "Document")

        self.clashA = make_test_document(Document, "clash", "application/pdf", simple_pdf, "clash.pdf", simple_pdf, "clash.pdf")
        self.clashB = make_test_document(Document, "clash", "image/jpeg", simple_jpg, "clash.jpg", simple_pdf, "clash_01.pdf")

        self.assertRaisesMessage(ValueError, "file already exists.", self.performMigration)