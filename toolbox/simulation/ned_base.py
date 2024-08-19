from hopp.type_dec import FromDictMixin
from abc import ABC, abstractmethod
from typing import Any, Dict, Final
import yaml
import attrs
from hopp.type_dec import attr_hopp_filter,attr_serializer

class BaseClassNed(FromDictMixin):
    @classmethod
    def get_model_defaults(cls) -> Dict[str, Any]:
        """Produces a dictionary of the keyword arguments and their defaults.

        Returns
        -------
        Dict[str, Any]
            Dictionary of keyword argument: default.
        """
        return {el.name: el.default for el in attrs.fields(cls)}

    def _get_model_dict(self) -> dict:
        """Convenience method that wraps the `attrs.asdict` method. Returns the object's
        parameters as a dictionary.

        Returns
        -------
        dict
            The provided or default, if no input provided, model settings as a dictionary.
        """
        # return attrs.asdict(self)
        return attrs.asdict(self,filter=attr_hopp_filter,value_serializer=attr_serializer)
    
    def to_file(self, output_file_path: str, filetype: str="YAML") -> None:
        """Converts the `Floris` object to an input-ready JSON or YAML file at `output_file_path`.

        Args:
            output_file_path (str): The full path and filename for where to save the file.
            filetype (str): The type to export: [YAML]
        """
        with open(output_file_path, "w+") as f:
            if filetype.lower() == "yaml":
                yaml.dump(self.as_dict(), f, default_flow_style=False)
            else:
                raise ValueError("Supported export filetype is YAML")
