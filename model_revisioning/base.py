from copy import deepcopy

from django.db import models
from django.db.models import Field
from django.db.models.base import ModelBase

from .options import RevisionOptions

excluded_field_names = ["original_object", "is_head", "parent_revision", "note"]


class RevisionBase(ModelBase):

    revision_model_by_model = {}

    def __new__(mcs, name, bases, attrs, **kwargs):

        if name == "RevisionModel":
            return super(RevisionBase, mcs).__new__(mcs, name, bases, attrs)

        attrs_copy = deepcopy(attrs)
        revisions_options = attrs.pop("Revisions", None)

        new_class = super().__new__(mcs, name, bases, attrs)
        new_class.add_to_class("_revisions", RevisionOptions(revisions_options))

        revision_attrs = {
            key: val for key, val in attrs_copy.items() if not isinstance(val, Field)
        }

        # If the model being revisioned inherits from an
        # abstract model we have to copy the fields from that
        for base in bases:
            if hasattr(base, "_meta") and base._meta.abstract:
                for field in base._meta.local_fields:
                    attrs_copy[field.name] = deepcopy(field)

        revisioned_fields = {
            key: attrs_copy[key] for key in new_class._revisions.fields
        }

        # We can not have any unique fields in revisions since many
        # revisions might have the same value for a unique field.
        for field in revisioned_fields.values():
            field._unique = False

        # Only include those model fields which are specified in RevisionsOptions
        revision_attrs.update(revisioned_fields)

        mcs._create_revision_model(name, revision_attrs, new_class)

        if new_class._revisions.soft_deletion:
            new_class.add_to_class("is_deleted", models.NullBooleanField(default=False))

        return new_class

    @classmethod
    def _create_revision_model(mcs, name, attrs, original_model, module=None):
        new_class_name = name + "Revision"
        attrs["__qualname__"] = new_class_name

        from .models import Revision

        bases = (Revision,)

        attrs["__module__"] = module if module else original_model.__module__

        revision_class = super().__new__(mcs, new_class_name, bases, attrs)

        revision_class.add_to_class(
            "original_object",
            models.ForeignKey(
                original_model, related_name="revisions", on_delete=models.CASCADE
            ),
        )
        original_model.revision_class = revision_class

        revision_class.original_model_class = original_model

        return revision_class
