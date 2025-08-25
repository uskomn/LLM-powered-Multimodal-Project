from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "student"

class UserLogin(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        orm_mode = True
        from_attributes = True