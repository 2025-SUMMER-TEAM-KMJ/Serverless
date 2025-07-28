# main.py
import jsonschema
from jsonschema import validate
from typing import List, Dict, Any, Optional, Union

# ==============================================================================
# 1. MasterCrawlerLog 클래스 (master_crawler_log.schema.json 기반)
# ==============================================================================
class MasterCrawlerLog:
    """
    크롤러 로그의 개별 항목 데이터를 관리하고 유효성을 검증하는 클래스.

    이 클래스는 최종 크롤러 로그 항목 스키마를 준수합니다.
    """

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "크롤러 로그 항목 스키마",
        "description": "크롤러가 처리할 개별 로그 항목의 구조를 정의합니다.",
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "format": "uri",
                "description": "수집 대상 URL"
            },
            "purposes": {
                "type": "array",
                "description": "하나의 URL에 대한 여러 수집 목적 목록",
                "items": {"type": "string"},
                "minItems": 1
            },
            "crawledAt": {
                "type": ["string", "null"],
                "format": "date-time",
                "description": "마지막으로 크롤링을 시도한 시각. 아직 처리되지 않았다면 null."
            }
        },
        "required": ["url", "crawledAt"]
    }

    def __init__(self, url: str, crawledAt: str, purposes: Optional[List[str]] = None):
        """
        CrawlerLogItem 인스턴스를 초기화합니다.

        Args:
            url (str): 수집 대상 URL.
            purposes (List[str]): 수집 목적 목록.
            crawledAt (Optional[str], optional): 마지막 크롤링 시각. Defaults to None.
        """
        self.url = url
        self.purposes = purposes
        self.crawledAt = crawledAt
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        """
        클래스 인스턴스를 JSON 스키마 구조의 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: 스키마 구조와 일치하는 딕셔너리.
        """
        return {
            "url": self.url,
            "purposes": self.purposes,
            "crawledAt": self.crawledAt
        }

    def _validate(self) -> None:
        """
        현재 인스턴스의 데이터 유효성을 검증합니다.
        
        Raises:
            ValueError: 데이터가 스키마에 맞지 않을 경우 발생합니다.
        """
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MasterCrawlerLog':
        """
        딕셔너리로부터 CrawlerLogItem 인스턴스를 생성합니다.

        Args:
            data (Dict[str, Any]): 스키마 구조를 따르는 딕셔너리.

        Returns:
            CrawlerLogItem: 생성된 클래스 인스턴스.
            
        Raises:
            ValueError: 입력된 딕셔너리가 스키마에 맞지 않을 경우 발생합니다.
        """
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e
        
        return cls(
            url=data['url'],
            purposes=data['purposes'],
            crawledAt=data.get('crawledAt')
        )

    def __repr__(self) -> str:
        """객체를 표현하는 문자열을 반환합니다."""
        return f"<CrawlerLogItem url='{self.url}' purposes={self.purposes}>"

# ==============================================================================
# 2. JobkoreaCoverLetter 클래스 (jobkorea_cover_letter.schema.json 기반)
# ==============================================================================
class JobkoreaCoverLetter:
    """
    자소서 데이터를 관리하고 유효성을 검증하는 클래스.
    
    이 클래스는 jobkorea_cover_letter.schema.json 스키마를 준수합니다.
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "자소서 스키마",
        "description": "AI 데이터로 제공되는 자소서 스키마",
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["accepted", "rejected", "unknown"]},
            "companyName": {"type": "string", "description": "지원 기업명"},
            "positionName": {"type": "string", "description": "지원 직무 또는 직무 설명"},
            "applicationAt": {"type": "string", "format": "date", "description": "지원 시기 (예: 2025-07-01)"},
            "applicant": {"type": "array", "description": "지원자 정보 키워드들", "items": {"type": "string"}},
            "essays": {
                "type": "array", "description": "자기소개서 문항 리스트",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "자기소개서 문항 (질문)"},
                        "answer": {"type": "string", "description": "해당 문항에 대한 작성 답변"},
                        "maxLength": {"type": "integer", "description": "문항의 최대 글자 수"}
                    },
                    "required": ["question", "answer"]
                }
            },
            "metadata": {
                "description": "크롤링 및 데이터 처리에 대한 메타 정보",
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "sourceUrl": {"type": "string", "format": "uri"},
                    "crawledAt": {"type": "string", "format": "date-time"}
                },
                "required": ["source", "sourceUrl", "crawledAt"]
            },
            "sourceData": {"type": ["object", "string"]}
        },
        "required": ["companyName", "positionName", "applicant", "essays", "metadata", "sourceData"]
    }

    def __init__(self, companyName: str, positionName: str, applicant: List[str], essays: List[Dict[str, Any]],
                 metadata: Dict[str, Any], sourceData: Union[Dict, str], status: Optional[str] = None,
                 applicationAt: Optional[str] = None):
        self.companyName = companyName
        self.positionName = positionName
        self.applicant = applicant
        self.essays = essays
        self.metadata = metadata
        self.sourceData = sourceData
        self.status = status
        self.applicationAt = applicationAt
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "companyName": self.companyName,
            "positionName": self.positionName,
            "applicant": self.applicant,
            "essays": self.essays,
            "metadata": self.metadata,
            "sourceData": self.sourceData
        }
        if self.status is not None:
            data['status'] = self.status
        if self.applicationAt is not None:
            data['applicationAt'] = self.applicationAt
        return data

    def _validate(self) -> None:
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobkoreaCoverLetter':
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e

        return cls(
            companyName=data['companyName'],
            positionName=data['positionName'],
            applicant=data['applicant'],
            essays=data['essays'],
            metadata=data['metadata'],
            sourceData=data['sourceData'],
            status=data.get('status'),
            applicationAt=data.get('applicationAt')
        )

# ==============================================================================
# 3. MasterJobPosting 클래스 (master_job_posting.schema.json 기반)
# ==============================================================================
class MasterJobPosting:
    """
    채용 공고 데이터를 관리하고 유효성을 검증하는 클래스.
    
    이 클래스는 master_job_posting.schema.json 스키마를 준수합니다.
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "채용 공고 스키마",
        "type": "object",
        "properties": {
            "metadata": {"type": "object", "required": ["source", "sourceUrl", "crawledAt"], "properties": {"source": {"type": "string"}, "sourceUrl": {"type": "string", "format": "uri"}, "crawledAt": {"type": "string", "format": "date-time"}}},
            "sourceData": {"type": ["object", "string"]},
            "externalUrl": {"type": "string", "format": "uri"},
            "status": {"type": "string", "enum": ["active", "closed"]},
            "due_time": {"type": ["string", "null"], "format": "date-time"},
            "detail": {"type": "object", "required": ["position", "main_tasks", "requirements"], "properties": {"position": {"type": "object", "required": ["jobGroup"], "properties": {"jobGroup": {"type": "string"}, "job": {"type": "array", "items": {"type": "string"}}}}, "intro": {"type": "string"}, "main_tasks": {"type": "string"}, "requirements": {"type": "string"}, "preferred_points": {"type": "string"}, "benefits": {"type": "string"}, "hire_rounds": {"type": "string"}}},
            "company": {"type": "object", "properties": {"features": {"type": "array", "items": {"type": "string"}}, "avgSalary": {"type": "integer"}, "avgEntrySalary": {"type": "integer"}, "address": {"type": "object", "required": ["full_location"], "properties": {"country": {"type": "string"}, "location": {"type": "string"}, "district": {"type": "string"}, "full_location": {"type": "string"}}}}},
            "skill_tags": {"type": "array", "items": {"type": "string"}},
            "title_images": {"type": "array", "items": {"type": "string", "format": "uri"}}
        },
        "required": ["metadata", "sourceData", "status", "detail", "company"]
    }

    def __init__(self, metadata: Dict[str, Any], sourceData: Union[Dict, str], status: str, detail: Dict[str, Any], company: Dict[str, Any],
                 externalUrl: Optional[str] = None, due_time: Optional[str] = None, skill_tags: Optional[List[str]] = None,
                 title_images: Optional[List[str]] = None):
        self.metadata = metadata
        self.sourceData = sourceData
        self.status = status
        self.detail = detail
        self.company = company
        self.externalUrl = externalUrl
        self.due_time = due_time
        self.skill_tags = skill_tags
        self.title_images = title_images
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "metadata": self.metadata,
            "sourceData": self.sourceData,
            "status": self.status,
            "detail": self.detail,
            "company": self.company
        }
        if self.externalUrl is not None: data['externalUrl'] = self.externalUrl
        if self.due_time is not None: data['due_time'] = self.due_time
        if self.skill_tags is not None: data['skill_tags'] = self.skill_tags
        if self.title_images is not None: data['title_images'] = self.title_images
        return data

    def _validate(self) -> None:
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MasterJobPosting':
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e
        
        return cls(
            metadata=data['metadata'],
            sourceData=data['sourceData'],
            status=data['status'],
            detail=data['detail'],
            company=data['company'],
            externalUrl=data.get('externalUrl'),
            due_time=data.get('due_time'),
            skill_tags=data.get('skill_tags'),
            title_images=data.get('title_images')
        )

# ==============================================================================
# 4. MasterUserProfile 클래스 (master_user_profile.schema.json 기반)
# ==============================================================================
class MasterUserProfile:
    """
    사용자 프로필 데이터를 관리하고 유효성을 검증하는 클래스.
    
    이 클래스는 master_user_profile.schema.json 스키마를 준수합니다.
    """
    schema = {
      "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "사용자 프로필 스키마", "type": "object",
      "properties": {
        "name": {"type": "string"}, "age": {"type": "integer", "minimum": 0}, "gender": {"type": "string", "enum": ["Male", "Female", "Other"]},
        "email": {"type": "string", "format": "email"}, "phone": {"type": "string"},
        "urls": {"type": "array", "items": {"type": "string", "format": "uri"}},
        "education": {"type": "array", "items": {"type": "object", "properties": {"schoolName": {"type": "string"}, "major": {"type": "string"}, "degree": {"type": "string", "enum": ["Associate", "Bachelor", "Master", "Doctorate"]}, "startDate": {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, "endDate": {"anyOf": [{"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, {"type": "null"}]}}, "required": ["schoolName", "major", "startDate"]}},
        "workExperience": {"type": "array", "items": {"type": "object", "properties": {"companyName": {"type": "string"}, "jobGroup": {"type": "string"}, "job": {"type": "string"}, "startDate": {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, "endDate": {"anyOf": [{"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, {"type": "null"}]}, "description": {"type": "string"}}, "required": ["companyName", "jobGroup", "job", "startDate"]}},
        "experience": {"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "link": {"type": "string", "format": "uri"}, "techStack": {"type": "array", "items": {"type": "string"}}, "startDate": {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, "endDate": {"anyOf": [{"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}, {"type": "null"}]}, "type": {"type": "string", "enum": ["Personal Project", "Open Source Contribution", "Tech Blog", "Presentation", "Study", "Other"]}}, "required": ["title", "description"]}},
        "competencies": {"type": "array", "items": {"type": "string"}},
        "preferredPosition": {"type": "array", "items": {"type": "object", "properties": {"jobGroup": {"type": "string"}, "job": {"type": "string"}}, "required": ["jobGroup"]}},
        "certifications": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "issueDate": {"type": "string", "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$"}}, "required": ["name", "issueDate"]}},
        "personalNarratives": {"type": "object", "properties": {"personality": {"type": "string"}, "values": {"type": "string"}, "psExperience": {"type": "string"}}}
      },
      "required": ["name", "age", "gender", "email", "phone"]
    }

    def __init__(self, name: str, age: int, gender: str, email: str, phone: str, 
                 urls: Optional[List[str]] = None, education: Optional[List[Dict]] = None, 
                 workExperience: Optional[List[Dict]] = None, experience: Optional[List[Dict]] = None, 
                 competencies: Optional[List[str]] = None, preferredPosition: Optional[List[Dict]] = None, 
                 certifications: Optional[List[Dict]] = None, personalNarratives: Optional[Dict] = None):
        self.name = name
        self.age = age
        self.gender = gender
        self.email = email
        self.phone = phone
        self.urls = urls
        self.education = education
        self.workExperience = workExperience
        self.experience = experience
        self.competencies = competencies
        self.preferredPosition = preferredPosition
        self.certifications = certifications
        self.personalNarratives = personalNarratives
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        data = {"name": self.name, "age": self.age, "gender": self.gender, "email": self.email, "phone": self.phone}
        if self.urls is not None: data["urls"] = self.urls
        if self.education is not None: data["education"] = self.education
        if self.workExperience is not None: data["workExperience"] = self.workExperience
        if self.experience is not None: data["experience"] = self.experience
        if self.competencies is not None: data["competencies"] = self.competencies
        if self.preferredPosition is not None: data["preferredPosition"] = self.preferredPosition
        if self.certifications is not None: data["certifications"] = self.certifications
        if self.personalNarratives is not None: data["personalNarratives"] = self.personalNarratives
        return data

    def _validate(self) -> None:
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MasterUserProfile':
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e
        
        return cls(
            name=data['name'], age=data['age'], gender=data['gender'], email=data['email'], phone=data['phone'],
            urls=data.get('urls'), education=data.get('education'), workExperience=data.get('workExperience'),
            experience=data.get('experience'), competencies=data.get('competencies'),
            preferredPosition=data.get('preferredPosition'), certifications=data.get('certifications'),
            personalNarratives=data.get('personalNarratives')
        )

# ==============================================================================
# 5. WantedJobPosting 클래스 (wanted_job_posting.schema.json 기반)
# ==============================================================================
class WantedJobPosting:
    """
    원티드 채용 공고 데이터를 관리하고 유효성을 검증하는 클래스.
    
    이 클래스는 wanted_job_posting.schema.json 스키마를 준수합니다.
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "채용 공고 스키마", "type": "object",
        "properties": {
            "metadata": {"type": "object", "required": ["source", "sourceUrl", "crawledAt"], "properties": {"source": {"type": "string"}, "sourceUrl": {"type": "string", "format": "uri"}, "crawledAt": {"type": "string", "format": "date-time"}}},
            "sourceData": {"type": ["object", "string"]},
            "externalUrl": {"type": "string", "format": "uri"},
            "status": {"type": "string", "enum": ["active", "closed"]},
            "due_time": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
            "detail": {"type": "object", "required": ["position", "main_tasks", "requirements"], "properties": {"position": {"type": "object", "required": ["jobGroup", "job"], "properties": {"jobGroup": {"type": "string"}, "job": {"type": "string"}}}, "intro": {"type": "string"}, "main_tasks": {"type": "string"}, "requirements": {"type": "string"}, "preferred_points": {"type": "string"}, "benefits": {"type": "string"}, "hire_rounds": {"type": "string"}}},
            "company": {"type": "object", "required": ["name", "address"], "properties": {"name": {"type": "string"}, "logo_img": {"anyOf": [{"type": "string", "format": "uri"}, {"type": "null"}]}, "address": {"type": "object", "required": ["full_location"], "properties": {"country": {"type": "string"}, "location": {"type": "string"}, "district": {"type": "string"}, "full_location": {"type": "string"}}}}},
            "skill_tags": {"type": "array", "items": {"type": "string"}},
            "title_images": {"type": "array", "items": {"type": "string", "format": "uri"}}
        },
        "required": ["metadata", "sourceData", "status", "detail", "company"]
    }

    def __init__(self, metadata: Dict, sourceData: Union[Dict, str], status: str, detail: Dict, company: Dict,
                 externalUrl: Optional[str] = None, due_time: Optional[str] = None, 
                 skill_tags: Optional[List[str]] = None, title_images: Optional[List[str]] = None):
        self.metadata = metadata
        self.sourceData = sourceData
        self.status = status
        self.detail = detail
        self.company = company
        self.externalUrl = externalUrl
        self.due_time = due_time
        self.skill_tags = skill_tags
        self.title_images = title_images
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        data = {"metadata": self.metadata, "sourceData": self.sourceData, "status": self.status, "detail": self.detail, "company": self.company}
        if self.externalUrl is not None: data['externalUrl'] = self.externalUrl
        if self.due_time is not None: data['due_time'] = self.due_time
        if self.skill_tags is not None: data['skill_tags'] = self.skill_tags
        if self.title_images is not None: data['title_images'] = self.title_images
        return data

    def _validate(self) -> None:
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WantedJobPosting':
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e
        
        return cls(
            metadata=data['metadata'], sourceData=data['sourceData'], status=data['status'],
            detail=data['detail'], company=data['company'], externalUrl=data.get('externalUrl'),
            due_time=data.get('due_time'), skill_tags=data.get('skill_tags'),
            title_images=data.get('title_images')
        )

# ==============================================================================
# 6. WantedCompanyProfile 클래스 (wanted_company_profile.schema.json 기반)
# ==============================================================================
class WantedCompanyProfile:
    """
    원티드 기업 정보 데이터를 관리하고 유효성을 검증하는 클래스.
    
    이 클래스는 wanted_company_profile.schema.json 스키마를 준수합니다.
    """
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "기업 정보 스키마", "type": "object",
        "properties": {
            "companyName": {"type": "string"},
            "source": {"type": "object", "required": ["url"], "properties": {"url": {"type": "string", "format": "uri"}, "platform": {"type": "string"}, "crawledAt": {"type": "string", "format": "date-time"}}},
            "profile": {"type": "object", "properties": {"features": {"type": "array", "items": {"type": "string"}}, "avgSalary": {"type": "integer"}, "avgEntrySalary": {"type": "integer"}, "address": {"type": "object", "required": ["full_location"], "properties": {"country": {"type": "string"}, "location": {"type": "string"}, "district": {"type": "string"}, "full_location": {"type": "string"}}}}},
            "metadata": {"type": "object", "required": ["source", "sourceUrl", "crawledAt"], "properties": {"source": {"type": "string"}, "sourceUrl": {"type": "string", "format": "uri"}, "crawledAt": {"type": "string", "format": "date-time"}}},
            "sourceData": {"type": ["object", "string"]}
        },
        "required": ["companyName", "source"]
    }

    def __init__(self, companyName: str, source: Dict, profile: Optional[Dict] = None, 
                 metadata: Optional[Dict] = None, sourceData: Optional[Union[Dict, str]] = None):
        self.companyName = companyName
        self.source = source
        self.profile = profile
        self.metadata = metadata
        self.sourceData = sourceData
        self._validate()

    def to_dict(self) -> Dict[str, Any]:
        data = {"companyName": self.companyName, "source": self.source}
        if self.profile is not None: data["profile"] = self.profile
        if self.metadata is not None: data["metadata"] = self.metadata
        if self.sourceData is not None: data["sourceData"] = self.sourceData
        return data

    def _validate(self) -> None:
        try:
            validate(instance=self.to_dict(), schema=self.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"데이터 검증 실패: {e.message}") from e

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WantedCompanyProfile':
        try:
            validate(instance=data, schema=cls.schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"입력 딕셔너리 검증 실패: {e.message}") from e
        
        return cls(
            companyName=data['companyName'], source=data['source'],
            profile=data.get('profile'), metadata=data.get('metadata'), sourceData=data.get('sourceData')
        )


# ==============================================================================
# 사용 예제 코드
# ==============================================================================
if __name__ == "__main__":
    
    print("="*20, "1. MasterCrawlerLog 예제", "="*20)
    valid_crawler_data = {"urls": [{"url": "https://example.com/job/123", "crawled": ["job_posting"]}]}
    invalid_crawler_data = {"urls": [{"crawled": ["job_posting"]}]} # 'url' 필드 누락
    
    # from_dict로 생성
    crawler_instance_1 = MasterCrawlerLog.from_dict(valid_crawler_data)
    print("from_dict 성공:", crawler_instance_1.to_dict())
    
    # __init__으로 생성
    crawler_instance_2 = MasterCrawlerLog(urls=[{"url": "https://example.com/job/456", "crawled": []}])
    print("__init__ 성공:", crawler_instance_2.to_dict())

    # 실패 예제
    try:
        MasterCrawlerLog.from_dict(invalid_crawler_data)
    except ValueError as e:
        print(f"from_dict 실패 (의도된 에러): {e}")

    print("\n" + "="*20, "2. MasterJobPosting 예제", "="*20)
    valid_job_posting_data = {
        "metadata": {"source": "Wanted", "sourceUrl": "https://example.com/posting/1", "crawledAt": "2025-07-26T12:00:00Z"},
        "sourceData": "<html>...</html>",
        "status": "active",
        "detail": {
            "position": {"jobGroup": "개발", "job": ["백엔드 개발자"]},
            "main_tasks": "API 서버 개발",
            "requirements": "Python, Django 경험"
        },
        "company": {
            "address": {"full_location": "경기도 성남시 분당구"}
        }
    }
    invalid_job_posting_data = { # 'status' 필드 누락
        "metadata": {"source": "Wanted", "sourceUrl": "https://example.com/posting/1", "crawledAt": "2025-07-26T12:00:00Z"},
        "sourceData": "<html>...</html>",
        "detail": {"position": {"jobGroup": "개발"}, "main_tasks": "...", "requirements": "..."},
        "company": {"address": {"full_location": "..."}}
    }
    
    # from_dict로 생성
    job_posting_instance = MasterJobPosting.from_dict(valid_job_posting_data)
    print("from_dict 성공:", job_posting_instance.to_dict()['status'])
    
    # 실패 예제
    try:
        MasterJobPosting.from_dict(invalid_job_posting_data)
    except ValueError as e:
        print(f"from_dict 실패 (의도된 에러): {e}")

    print("\n" + "="*20, "3. MasterUserProfile 예제", "="*20)
    valid_user_data = {
        "name": "홍길동", "age": 28, "gender": "Male", "email": "test@example.com", "phone": "010-1234-5678",
        "workExperience": [
            {"companyName": "카카오", "jobGroup": "개발", "job": "소프트웨어 엔지니어", "startDate": "2023-01"}
        ]
    }
    invalid_user_data = {"name": "임꺽정", "age": 30, "gender": "Male"} # email, phone 필드 누락

    # from_dict로 생성
    user_instance = MasterUserProfile.from_dict(valid_user_data)
    print("from_dict 성공:", user_instance.name)
    
    # __init__으로 생성
    user_instance_2 = MasterUserProfile(name="김철수", age=25, gender="Male", email="chulsoo@example.com", phone="010-9876-5432")
    print("__init__ 성공:", user_instance_2.to_dict()['name'])

    # 실패 예제
    try:
        MasterUserProfile.from_dict(invalid_user_data)
    except ValueError as e:
        print(f"from_dict 실패 (의도된 에러): {e}")