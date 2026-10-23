"""Base contract primitives and end-to-end identifier types (compatible with Pydantic v1 & v2)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
import pydantic
from pydantic import BaseModel, Field

PYDANTIC_V2 = int(pydantic.__version__.split(".")[0]) >= 2

if PYDANTIC_V2:
    from typing import Annotated
    from pydantic import ConfigDict, StringConstraints, field_validator, model_validator

    def _id(prefix: str, digits: str = "[0-9]{3,5}"):
        return Annotated[str, StringConstraints(pattern=f"^{prefix}-{digits}$")]
else:
    from pydantic import constr, validator, root_validator  # type: ignore

    def _id(prefix: str, digits: str = "[0-9]{3,5}"):
        return constr(regex=f"^{prefix}-{digits}$")


def regex_field(pattern: str, **kwargs: Any) -> Any:
    if PYDANTIC_V2:
        return Field(pattern=pattern, **kwargs)
    return Field(regex=pattern, **kwargs)


class Contract(BaseModel):
    """Base for every inter-stage artifact: immutable, no unknown fields (Pydantic v1 & v2 compatible)."""

    if PYDANTIC_V2:
        model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    else:
        class Config:
            extra = "forbid"
            allow_mutation = False
            anystr_strip_whitespace = True

    def dump_json_dict(self) -> dict[str, Any]:
        if PYDANTIC_V2:
            return self.model_dump(mode="json")  # type: ignore[attr-defined]
        return json.loads(self.json())

    def to_pretty_json(self) -> str:
        return json.dumps(self.dump_json_dict(), indent=2, sort_keys=True)

    @classmethod
    def parse_obj_compat(cls, data: Any):
        if PYDANTIC_V2:
            return cls.model_validate(data)  # type: ignore[attr-defined]
        return cls.parse_obj(data)

    @classmethod
    def parse_json_compat(cls, raw_json: str):
        return cls.parse_obj_compat(json.loads(raw_json))

    def copy_with(self, update: dict[str, Any]):
        if PYDANTIC_V2:
            return self.model_copy(update=update)  # type: ignore[attr-defined]
        return self.copy(update=update)

    def canonical_json(self) -> str:
        return json.dumps(self.dump_json_dict(), sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_obj(data: Any) -> str:
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


EpicId = _id("EP")
StoryId = _id("ST")
TaskId = _id("TSK")
ServiceId = _id("SVC")
NfrId = _id("NFR")
AdrId = _id("ADR")
AcId = _id("AC", "[0-9]{3,5}-[0-9]{2}")
ModuleId = _id("MOD")
ContractId = _id("CON")
BuildId = _id("BLD")
TestId = _id("TST")
FindingId = _id("FND")
RiskId = _id("RSK")
DtoId = _id("DTO")
TableId = _id("TBL")
ErrorId = _id("ERR")
SecId = _id("SEC")
ConfigId = _id("CFG")
InvariantId = _id("INV")
