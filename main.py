import os
from asyncio import current_task
from os.path import dirname, abspath
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from google.cloud import translate
from pydantic import BaseModel
from pydantic import BaseSettings
from sqlalchemy import select, desc, asc, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, async_scoped_session
from models import Word

BASE_DIR = dirname(abspath(__file__))
app = FastAPI()


class Settings(BaseSettings):
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str
    google_project_id: str

    class Config:
        env_file = os.path.join(BASE_DIR, "defaults.env")
        env_prefix = "app_"
        load_dotenv(
            dotenv_path=os.path.join(BASE_DIR, "local.env"), override=True, verbose=True, interpolate=True
        )


settings = Settings()
DB_URI = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
engine = create_async_engine(
    url=DB_URI, future=True, echo=True
)


def get_session():
    async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    _session = async_scoped_session(
        async_session_factory, scopefunc=current_task
    )
    return _session



class WordShort(BaseModel):
    word: str
    examples: List[str] = []


class WordFull(WordShort):
    definitions: List[str] = []
    synonyms: List[str] = []
    translations: List[str] = []


@app.get("/word/{word}", response_model=WordFull)
async def get_word_details(word: str):
    if len(word.split(" ")) > 1:
        raise HTTPException(status_code=400, detail="Must be just a single word")
    curr_session = get_session()
    async with curr_session() as session_:
        result = await session_.execute(
            select(Word).where(Word.word == word).limit(1)
        )
        db_word = result.scalars().first()

    if db_word:
        return WordFull(
            word=db_word.word,
            definitions=db_word.definitions,
            synonyms=db_word.synonyms,
            translations=db_word.translations,
            examples=db_word.examples,
        )
    else:
        client = translate.TranslationServiceAsyncClient()
        location = "global"
        parent = f"projects/{settings.google_project_id}/locations/{location}"
        response = await client.translate_text(
            request={
                "parent": parent,
                "contents": [word],
                "mime_type": "text/plain",
                "source_language_code": "en-US",
                "target_language_code": "ru",
            }
        )
        translations = []
        for translation in response.translations:
            translations.append(translation.translated_text)
        definitions = ["Definition 1", "Definition 2"]
        synonyms = ["Synonym 1", "Synonym 2"]
        examples = ["Example 1", "Example 2"]
        # translations = ["translations1", "translations2"]
        async with curr_session() as session_:
            new_word = Word(
                word=word,
                definitions=definitions,
                synonyms=synonyms,
                translations=translations,
                examples=examples,
            )
            session_.add(new_word)
            await session_.commit()

        return WordFull(
            word=word,
            definitions=definitions,
            synonyms=synonyms,
            translations=translations,
            examples=examples,
        )


def list_response_prepare(word_list, is_full):
    response = []
    if is_full:
        for value in word_list:
            response.append(
                WordFull(
                    word=value.word,
                    definitions=value.definitions,
                    synonyms=value.synonyms,
                    translations=value.translations,
                    examples=value.examples,
                )
            )
    else:
        for value in word_list:
            response.append(
                WordShort(
                    word=value.word,
                    examples=value.examples,
                )
            )

    return response


@app.get("/words")
async def get_word_list(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, gt=0, le=100),
        sort: str = Query(
            None,
            example="-word",
            description="May sort by field name use field name for asc sorting and field name with minus for desc sorting"
        ),
        filter_: str = Query(None, alias="filter"),
        is_full: int = Query(0, gt=-1, lt=2, description="Set 1 to show full, set 0 or nothing to show short")
):
    curr_session = get_session()
    async with curr_session() as session_:
        q = select(Word)
        if filter_:
            q = q.where(Word.word.ilike(f'%{filter_}%'))

        if sort:
            if sort.startswith("-"):
                order_by = desc(sort[1:])
            else:
                order_by = asc(sort)
            q = q.order_by(order_by)

        query = await session_.execute(
            q.offset(offset).limit(limit)
        )
        word_list = query.scalars().all()

    response = list_response_prepare(word_list, is_full)
    return response


@app.delete("/word/{word}")
async def delete_word(word: str):
    curr_session = get_session()
    async with curr_session() as session_:
        query = delete(Word).where(Word.word == word)
        await session_.execute(query)
        await session_.commit()
    return {"message": f"Word '{word}' deleted successfully"}
