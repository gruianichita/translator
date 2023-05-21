import os
import time
from asyncio import current_task
from os.path import dirname, abspath
from typing import List

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from lxml import etree
from pydantic import BaseModel
from pydantic import BaseSettings
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
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


def parse_google_translate(word, source_lang, translate_lang):
    translations = []
    url = f"https://translate.google.com/?sl={source_lang}&tl={translate_lang}&text={word}&op=translate"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    today_tag = "c-wiz"
    html_file_name = f"translate_page_word_{word}_{source_lang}_{translate_lang}.html"
    while True:
        try:
            try:
                translation_xpath = f"/html/body/{today_tag}/div/div[2]/{today_tag}/div[2]/{today_tag}/div[1]/div[2]/div[3]/{today_tag}[2]/div/div[9]/div/div[1]/span[1]/span/span"
                main_translation = driver.find_element(By.XPATH, translation_xpath)
            except NoSuchElementException:
                button_xpath = f"/html/body/{today_tag}/div/div[2]/{today_tag}/div[2]/{today_tag}/div[1]/div[2]/div[3]/{today_tag}[2]/div/div[7]/div[2]/button"
                retry_button = driver.find_element(By.XPATH, button_xpath)
                retry_button.click()
                time.sleep(1)
                continue
            try:
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, "html.parser")
                with open(html_file_name, "w", encoding="utf-8") as file:
                    file.write(soup.prettify())

                with open(html_file_name, 'r') as file:
                    html_content = file.read()

                all_translations_table_xpath = f"/html/body/{today_tag}/div/div[2]/{today_tag}/div[2]/{today_tag}/div[2]/{today_tag}/div/div/div[1]/div/div/table" + "/tbody"
                root = etree.HTML(html_content)
                xpath_expression = all_translations_table_xpath
                tbody_elements = root.xpath(xpath_expression)

                for tbody in tbody_elements:
                    tr_elements = tbody.xpath('./tr')
                    for idx, tr in enumerate(tr_elements, start=1):
                        if idx == 1:
                            td_text = tr.xpath(f"./th[2]/div/span[2]")
                            if not td_text:
                                td_text = tr.xpath(f"./th/div/div/span[2]")
                        else:
                            td_text = tr.xpath(f"./th/div/span[2]")
                            if not td_text:
                                td_text = tr.xpath(f"./th/div/div/span[2]")
                        translations.append(td_text[0].text.replace('\n', '').replace(' ', ''))
                translations = translations or [main_translation.text]
                break
            except NoSuchElementException:
                driver.quit()
                raise HTTPException(status_code=400, detail="Cannot translate, some error with parsing, try again")
        except ElementNotInteractableException:
            driver.quit()
            raise HTTPException(status_code=400, detail="Cannot translate, some error with parsing, try again")
    driver.quit()
    if os.path.exists(html_file_name):
        os.remove(html_file_name)
    return translations


@app.get("/word", response_model=WordFull)
async def get_word_details(
        word: str = Query(..., min_length=1),
        source_lang: str = Query(..., min_length=2, max_length=2),
        translate_lang: str = Query(..., min_length=2, max_length=2)):
    if len(word.split(" ")) > 1:
        raise HTTPException(status_code=400, detail="Must be just a single word")

    source_lang_lowercase = source_lang.lower()
    translate_lang_lowercase = translate_lang.lower()

    curr_session = get_session()
    async with curr_session() as session_:
        result = await session_.execute(
            select(Word).where(
                Word.word == word,
                Word.source_language == source_lang_lowercase,
                Word.translate_language == translate_lang_lowercase
            ).limit(1)
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
        translations = parse_google_translate(word, source_lang_lowercase, translate_lang_lowercase)
        # TODO: definitions, synonyms, and examples the same as translations
        definitions = ["Definition 1", "Definition 2"]
        synonyms = ["Synonym 1", "Synonym 2"]
        examples = ["Example 1", "Example 2"]

        async with curr_session() as session_:
            new_word = Word(
                word=word,
                definitions=definitions,
                synonyms=synonyms,
                translations=translations or [],
                examples=examples,
                source_language=source_lang_lowercase,
                translate_language=translate_lang_lowercase,
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
