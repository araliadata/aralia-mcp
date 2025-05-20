from pydantic import BaseModel
from typing import List
from typing_extensions import Literal, Annotated

# aralia_search_agent
class datasets_extract_output(BaseModel):
    dataset_key: list[str]
    dataset_name: list[str]

# analytics_execution_agent
class dataset_space_info(BaseModel):
    id: str
    region: Annotated[Literal["Taiwan", "America"], "Where dataset is from."]
    language: Annotated[Literal["zh-tw", "zh-cn", "en"],
                        "Language of the dataset."]


class dataset_space_info_list(BaseModel):
    datasets: List[dataset_space_info]


class x(BaseModel):
    columnID: str
    displayName: str
    type: str
    format: str


class y(BaseModel):
    columnID: str
    displayName: str
    calculation: str

class filter(BaseModel):
    columnID: str
    displayName: str
    type: str
    format: str
    operator: str
    value: list[str]

class query(BaseModel):
    sourceURL: str
    id: str
    name: str
    x: list[x]
    y: list[y]
    filter: list[filter]

class query_list(BaseModel):
    querys: list[query]
