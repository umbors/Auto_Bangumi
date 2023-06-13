import logging

from module.database.connector import DataConnector
from module.models import BangumiData
from module.ab_decorator import locked

logger = logging.getLogger(__name__)


class BangumiDatabase(DataConnector):
    def __init__(self):
        super().__init__()
        self.__table_name = "bangumi"

    def update_table(self):
        db_data = self.__data_to_db(BangumiData())
        self._update_table(self.__table_name, db_data)

    @staticmethod
    def __data_to_db(data: BangumiData) -> dict:
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    @staticmethod
    def __db_to_data(db_data: dict) -> BangumiData:
        for key, item in db_data.items():
            if isinstance(item, int):
                if key not in ["id", "offset", "season", "year"]:
                    db_data[key] = bool(item)
            elif key in ["filter", "rss_link"]:
                db_data[key] = item.split(",")
        return BangumiData(**db_data)

    def __fetch_data(self) -> list[BangumiData]:
        values = self._cursor.fetchall()
        if values is None:
            return []
        keys = [x[0] for x in self._cursor.description]
        dict_data = [dict(zip(keys, value)) for value in values]
        return [self.__db_to_data(x) for x in dict_data]

    def insert(self, data: BangumiData):
        if self.__check_exist(data):
            self.update_one(data)
        else:
            db_data = self.__data_to_db(data)
            db_data["id"] = self.gen_id()
            self._insert(db_data=db_data, table_name=self.__table_name)
            logger.debug(f"[Database] Insert {data.official_title} into database.")

    def insert_list(self, data: list[BangumiData]):
        _id = self.gen_id()
        for i, item in enumerate(data):
            item.id = _id + i
        data_list = [self.__data_to_db(x) for x in data]
        self._insert_list(data_list=data_list, table_name=self.__table_name)
        logger.debug(f"[Database] Insert {len(data)} bangumi into database.")

    def update_one(self, data: BangumiData) -> bool:
        db_data = self.__data_to_db(data)
        return self._update(db_data=db_data, table_name=self.__table_name)

    def update_list(self, data: list[BangumiData]):
        data_list = [self.__data_to_db(x) for x in data]
        self._update_list(data_list=data_list, table_name=self.__table_name)

    @locked
    def update_rss(self, title_raw, rss_set: str):
        # Update rss and added
        self._cursor.execute(
            """
            UPDATE bangumi 
            SET rss_link = :rss_link, added = 0
            WHERE title_raw = :title_raw
            """,
            {"rss_link": rss_set, "title_raw": title_raw},
        )
        self._conn.commit()
        logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")

    def update_poster(self, title_raw, poster_link: str):
        self._cursor.execute(
            """
            UPDATE bangumi 
            SET poster_link = :poster_link
            WHERE title_raw = :title_raw
            """,
            {"poster_link": poster_link, "title_raw": title_raw},
        )
        self._conn.commit()
        logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    def delete_one(self, _id: int) -> bool:
        self._cursor.execute(
            """
            DELETE FROM bangumi WHERE id = :id
            """,
            {"id": _id},
        )
        self._conn.commit()
        logger.debug(f"[Database] Delete bangumi id: {_id}.")
        return self._cursor.rowcount == 1

    def delete_all(self):
        self._delete_all(self.__table_name)

    def search_all(self) -> list[BangumiData]:
        dict_data = self._search_datas(self.__table_name)
        return [self.__db_to_data(x) for x in dict_data]

    def search_id(self, _id: int) -> BangumiData | None:
        condition = {"id": _id}
        dict_data = self._search_data(table_name=self.__table_name, condition=condition)
        if dict_data is None:
            return None
        return self.__db_to_data(dict_data)

    def search_official_title(self, official_title: str) -> BangumiData | None:
        dict_data = self._search_data(
            table_name=self.__table_name, condition={"official_title": official_title}
        )
        if dict_data is None:
            return None
        return self.__db_to_data(dict_data)

    def match_poster(self, bangumi_name: str) -> str:
        condition = {"_custom_condition": "INSTR(:bangumi_name, official_title) > 0"}
        keys = ["official_title", "poster_link"]
        data = self._search_data(
            table_name=self.__table_name,
            keys=keys,
            condition=condition,
        )
        if not data:
            return ""
        official_title, poster_link = data
        if not poster_link:
            return ""
        return poster_link

    def match_list(self, torrent_list: list, rss_link: str) -> list:
        # Match title_raw in database
        keys = ["title_raw", "rss_link", "poster_link"]
        match_datas = self._search_datas(
            table_name=self.__table_name,
            keys=keys,
        )
        if not match_datas:
            return torrent_list
        # Match title
        i = 0
        while i < len(torrent_list):
            torrent = torrent_list[i]
            for match_data in match_datas:
                if match_data.get("title_raw") in torrent.name:
                    if rss_link not in match_data.get("rss_link"):
                        match_data["rss_link"] += f",{rss_link}"
                        self.update_rss(match_data.get("title_raw"), match_data.get("rss_link"))
                    if not match_data.get("poster_link"):
                        self.update_poster(match_data.get("title_raw"), torrent.poster_link)
                    torrent_list.pop(i)
                    break
            else:
                i += 1
        return torrent_list

    def not_complete(self) -> list[BangumiData]:
        # Find eps_complete = False
        condition = {"eps_collect": 0}
        dict_data = self._search_datas(
            table_name=self.__table_name,
            condition=condition,
        )
        return [self.__db_to_data(x) for x in dict_data]

    def not_added(self) -> list[BangumiData]:
        condition = {"added": 0, "rule_name": None, "save_path": None}
        dict_data = self._search_datas(
            table_name=self.__table_name,
            condition=condition,
        )
        return [self.__db_to_data(x) for x in dict_data]

    def gen_id(self) -> int:
        self._cursor.execute(
            """
            SELECT id FROM bangumi ORDER BY id DESC LIMIT 1
            """
        )
        data = self._cursor.fetchone()
        if data is None:
            return 1
        return data[0] + 1

    def __check_exist(self, data: BangumiData):
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE official_title = :official_title
            """,
            {"official_title": data.official_title},
        )
        values = self._cursor.fetchone()
        if values is None:
            return False
        return True

    def __check_list_exist(self, data_list: list[BangumiData]):
        for data in data_list:
            if self.__check_exist(data):
                return True
        return False

if __name__ == '__main__':
    with BangumiDatabase() as db:
        print(db.not_added())
        print(db.not_complete())