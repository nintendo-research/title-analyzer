
from typing import Any, Self

import enum
import json
import os
import types
import typing


def is_none(type: Any) -> bool:
    return type is None or type == types.NoneType


class ValidationError(Exception):
    pass


class Serializer:
    """Base class for serializable objects."""

    _filename: str | None
    """The cached filename."""

    _current_field_name: str | None
    """This is used for error messages."""

    def __init__(self, *args, **kwargs):
        self._filename = None
        self._current_field_name = None

        self.reset(*args, **kwargs)
    
    def reset(self, *args, **kwargs) -> None:
        """Initializes all fields to their default values."""
        for k, v in self.__class__.__annotations__.items():
            setattr(self, k, self._default_value(v))
        self.initialize()
        for k, v in zip(self.__class__.__annotations__, args):
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def initialize(self) -> None:
        """
        Initializes the members of the object. May be implemented by subclasses.
        """
        pass

    def encode(self) -> dict[Any, Any]:
        """Serializes the object to JSON."""
        data = {}
        for name, value in self.__class__.__annotations__.items():
            self._current_field_name = name
            data[name] = self._encode_value(value, getattr(self, name))
        return data
    
    def decode(self, data: dict[Any, Any]) -> None:
        """Deserializes the object."""
        self.reset()
        for name, value in self.__class__.__annotations__.items():
            self._current_field_name = name
            setattr(self, name, self._decode_value(value, data.get(name)))
    
    def _default_value(self, type: Any) -> Any:
        """Returns the default value for the given type hint."""
        origin = typing.get_origin(type)
        args = typing.get_args(type)

        if origin is not None:
            if issubclass(origin, types.UnionType):
                if any(is_none(arg) for arg in args):
                    return None
                return self._default_value(args[0])
            return type()
        
        if is_none(type):
            return None
        
        if issubclass(type, enum.Enum):
            return list(type)[0]

        return type()
    
    def _make_validation_error(self, type: Any, value: Any) -> ValidationError:
        name = f"{self.__class__.__name__}.{self._current_field_name}"
        message = f"Expected {type}, got {value} in {name}"
        return ValidationError(message)
    
    def _encode_value(self, type: Any, value: Any) -> Any:
        """Serializes the given value to a JSON object."""
        origin = typing.get_origin(type)
        if origin is not None:
            return self._encode_generic(type, value)

        if is_none(type):
            if value is not None:
                raise self._make_validation_error(type, value)
            return None
        
        if issubclass(type, Serializer):
            if not isinstance(value, type):
                raise self._make_validation_error(type, value)
            return value.encode()
        
        if issubclass(type, bytes):
            if not isinstance(value, bytes):
                raise self._make_validation_error(type, value)
            return value.hex()
        
        if not isinstance(value, type):
            raise self._make_validation_error(type, value)
        
        return value
    
    def _encode_generic(self, type: Any, value: Any) -> Any:
        origin = typing.get_origin(type)
        args = typing.get_args(type)

        if issubclass(origin, list):
            if not isinstance(value, list):
                raise self._make_validation_error(type, value)
            if len(args) != 1:
                raise ValidationError(
                    "List requires exactly one type argument"
                )
            return self._encode_list(args[0], value)
        
        if issubclass(origin, dict):
            if not isinstance(value, dict):
                raise self._make_validation_error(type, value)
            if len(args) != 2:
                raise ValidationError(
                    "Dictionary requires exactly two type arguments"
                )
            return self._encode_dict(args[0], args[1], value)
        
        if issubclass(origin, types.UnionType):
            for subtype in args:
                try:
                    return self._encode_value(subtype, value)
                except ValidationError:
                    pass
            raise ValidationError("No suitable union candidate was found")
        
        raise ValidationError(f"Unsupported generic type: {type}")

    def _decode_value(self, type: Any, value: Any) -> Any:
        origin = typing.get_origin(type)
        if origin is not None:
            return self._decode_generic(type, value)
        
        if is_none(type):
            if value is not None:
                raise self._make_validation_error("null", value)
            return None
        
        if issubclass(type, Serializer):
            if not isinstance(value, dict):
                raise self._make_validation_error(type, value)
            return type.parse(value)
        
        if type == bytes:
            if not isinstance(value, str):
                raise self._make_validation_error("a hex string", value)
            return bytes.fromhex(value)
        
        if type == float:
            if not isinstance(value, (float, int)):
                raise self._make_validation_error("a number", value)
            return float(value)

        if type == int:
            if isinstance(value, str):
                if not value.isdecimal():
                    self._make_validation_error("an integer", value)
                return int(value)
        
        if issubclass(type, enum.Enum):
            return type(value)
        
        if not isinstance(value, type):
            raise self._make_validation_error(type, value)
        
        return value
    
    def _decode_generic(self, type: Any, value: Any) -> Any:
        origin = typing.get_origin(type)
        args = typing.get_args(type)

        if issubclass(origin, list):
            if not isinstance(value, list):
                raise ValidationError(f"Expected {type}, got {value}")
            if len(args) != 1:
                raise ValidationError(
                    "List requires exactly one type argument"
                )
            return self._decode_list(args[0], value)
        
        if issubclass(origin, dict):
            if not isinstance(value, dict):
                raise ValidationError(f"Expected {type}, got {value}")
            if len(args) != 2:
                raise ValidationError(
                    "Dictionary requires exactly two type arguments, got " \
                    f"{type}"
                )
            return self._decode_dict(args[0], args[1], value)
        
        if issubclass(origin, types.UnionType):
            for subtype in args:
                try:
                    return self._decode_value(subtype, value)
                except ValidationError:
                    pass
            raise ValidationError(f"Expected {type}, got {value}")
        
        raise ValidationError(f"Unsupported generic type: {type}")
    
    def _encode_list(self, type: Any, value: Any) -> list[Any]:
        return [self._encode_value(type, v) for v in value]
    
    def _decode_list(self, type: Any, value: list[Any]) -> Any:
        return [self._decode_value(type, v) for v in value]
        
    def _encode_dict(
        self, keytype: Any, valuetype: Any, value: dict[Any, Any]
    ) -> dict[Any, Any]:
        return {
            self._encode_value(keytype, k): self._encode_value(valuetype, v) \
                for k, v in value.items()
        }
        
    def _decode_dict(
        self, keytype: Any, valuetype: Any, value: dict[Any, Any]
    ) -> dict[Any, Any]:
        return {
            self._decode_value(keytype, k): self._decode_value(valuetype, v) \
                for k, v in value.items()
        }
    
    def save(self, filename: str | None = None) -> None:
        if filename is None:
            if self._filename is None:
                raise ValueError("A filename must be provided")
            filename = self._filename

        data = self.encode()
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    
    def load(self, filename: str) -> None:
        with open(filename) as f:
            self.decode(json.load(f))

        self._filename = filename

    def load_if_exists(self, filename: str) -> None:
        if os.path.isfile(filename):
            self.load(filename)

    @classmethod
    def fromfile(cls, filename: str) -> Self:
        instance = cls()
        instance.load(filename)
        return instance

    @classmethod
    def parse(cls, data: Any) -> Self:
        instance = cls()
        instance.decode(data)
        return instance
