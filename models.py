from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    source_id: str = Field(description="原始帖子的 id")
    title: str = Field(description="岗位标题")
    company: str | None = Field(default=None, description="公司名，没有就 null")
    city: str | None = Field(default=None, description="城市，例如 深圳")
    remote: bool = Field(default=False, description="是否远程")
    salary: str | None = Field(default=None, description="薪资原文，例如 15-25K")
    skills: list[str] = Field(default_factory=list, description="明确提到的技术名词")
    is_ai_related: bool = Field(default=False, description="是否 AI / 大模型相关")
    summary: str = Field(description="一句话概括，不超过 30 字")


class ExtractionResult(BaseModel):
    jobs: list[JobPosting]