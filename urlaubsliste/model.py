from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from utils import deep_merge


class List:
    def __init__(self, raw: dict, path: Optional[str | Path] = None):
        """
        Do NOT use the `path` argument to create a List object from Path.
        Use `List.from_file()` for this, the constructor `path` argument
        exists to store the path where the List is at. Can be None if
        created a blank list with `List.new()`
        """
        self.raw = raw
        self.path = path
        self._orm = None

    @classmethod
    def from_file(cls, path: str | Path) -> "List":
        with open(path, "r") as fp:
            raw = json.load(fp)
        return cls(raw, path)

    @classmethod
    def new(cls, name: str) -> "List":
        raw = {
            "base_list": None,
            "name": name,
            "structure": {
                "categories": {}
            }
        }
        return cls(raw)

    def add_category(self, category_name: str):
        self.orm.structure.categories[category_name] = []

    def remove_category(self, category_name: str):
        self.orm.structure.categories.pop(category_name)

    def rename_category(self, category_name: str, new_category_name: str):
        content = self.orm.structure.categories[category_name]
        self.orm.structure.categories[new_category_name] = content
        self.orm.structure.categories.pop(category_name)

    def change_baselist(self, new_path: Path | str):
        self.orm.base_list = str(Path(new_path).resolve())

    def remove_baselist(self):
        self.orm.base_list = None

    def change_name(self, new_name: str):
        self.orm.name = new_name

    @property
    def name(self) -> str:
        return self.orm.name

    @property
    def categories(self) -> list[str]:
        return list(self.orm.structure.categories.keys())

    @property
    def parent(self) -> Path | None:
        if self.orm.base_list is None:
            return None
        else:
            return Path(self.orm.base_list)

    @property
    def orm(self) -> "AnnotatedORM":
        self._orm = AnnotatedORM(self.raw)
        return self._orm

    def get_items_for_category(self, category: str) -> list[Optional[str]]:
        return self.orm.structure.categories[category]

    def get_amount_of_items_for_category(self, category: str) -> int:
        return len(self.get_items_for_category(category))

    def serialize(self) -> str:
        return json.dumps(self.raw)

    def get_raw_extended_with_parent(self) -> dict:
        parent = self.orm.base_list
        if parent is None:
            return self.raw
        with open(parent, mode="r") as fp:
            parent_raw = json.load(fp)
        merged_parent_list = List(
            List(parent_raw).get_raw_extended_with_parent()
        )
        categories_self = self.orm.structure.categories
        categories_parent = merged_parent_list.orm.structure.categories
        merged_categories = deep_merge(categories_self, categories_parent)
        full_raw = {
            "name": self.orm.name,
            "base_list": self.orm.base_list,
            "structure": {
                "categories": merged_categories
            }
        }
        return full_raw


class AnnotatedORM:
    def __init__(self, data: dict):
        self.data = data
        self.structure = AnnotatedStructure(data["structure"])

    @property
    def base_list(self):
        return self.data["base_list"]

    @base_list.setter
    def base_list(self, value: str | Path | None):
        if value is None:
            self.data["base_list"] = None
            return
        value = Path(value)
        if not value.exists():
            raise FileNotFoundError("The file doesn't exist.")
        if List.from_file(value).orm.name == self.name:
            raise ValueError("Both Lists have the same Name.")
        self.data["base_list"] = str(value)

    @property
    def name(self):
        return self.data["name"]

    @name.setter
    def name(self, value):
        self.data["name"] = value


class AnnotatedStructure:
    def __init__(self, structure: dict):
        self.categories: dict[str, list[Optional[str]]] = structure[
            "categories"
        ]
