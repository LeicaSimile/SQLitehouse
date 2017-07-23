# -*- coding: utf-8 -*-
import random
import sqlite3
from contextlib import closing

def clean(line):
    """ Strip a string of non-alphanumerics (except underscores).
    Can use to clean strings before using them in a database query.

    Args:
        line(unicode): String to clean.

    Returns:
        line(unicode): A string safe to use in a database query.

    Examples:
        >>> clean("Robert'); DROP TABLE Students;")
        RobertDROPTABLEStudents
        
    """
    return "".join(char for char in line if (char.isalnum() or "_" == char))


class Database(object):
    """ For reading and writing records in a SQLite database.

    Args:
        dbFile(unicode): The filepath of the database.
        
    """
    
    def __init__(self, db_file):
        self.db = db_file

    def get_column(self, header, table, maximum=None):
        """ Gets fields under a column header.

        Args:
            header(unicode): Name of column's header.
            table(unicode): Name of table.
            maximum(int, optional): Maximum amount of fields to fetch.

        Returns:
            fields(list): List of fields under header.
        """
        fields = []
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.row_factory = lambda cursor, row: row[0]
            c = connection.cursor()
            if maximum:
                c.execute(f"SELECT {header} FROM {table} LIMIT ?", [maximum])
            else:
                c.execute(f"SELECT {header} FROM {table}")
            fields = c.fetchall()
        
        return fields

    def get_field(self, field_id, header, table):
        """ Gets the field under the specified header by its primary key value.

        Args:
            field_id(int, str): Unique ID of line the field is in.
            header(unicode): Header of the field to fetch.
            table(unicode): Name of table to look into.

        Returns:
            The desired field, or None if the lookup failed.

        Raises:
            TypeError: If field_id doesn't exist in the table.
        
        Examples:
            >>> get_field(123, "firstname", "kings")
            Adgar
        """
        header = clean(header)
        table = clean(table)
        field = None
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

            statement = f"SELECT {header} FROM {table} WHERE id=?"
            logger.debug(statement)
            c.execute(statement, [field_id])

            try:
                field = c.fetchone()[0]
            except TypeError:
                logger.exception(f"ID '{field_id}' was not in table '{table}'")
        
        return field

    def get_ids(self, table, conditions=None, splitter=","):
        """ Gets the IDs that fit within the specified conditions.

        Gets all IDs if conditions is None.

        Args:
            table(unicode): Name of table to look into.
            conditions(list, optional): Categories you want to filter the line by:
                {"header of categories 1": "category1,category2",
                 "header of category 2": "category3"}
                Multiple categories under a single header are separated with a comma.

        Returns:
            ids(list): List of IDs that match the categories.

        Raises:
            OperationalError: If table or header doesn't exist.
            TypeError: If category is neither None nor a dictionary.

        Examples:
            >>> get_ids({"type": "greeting"})
            [1, 2, 3, 5, 9, 15]  # Any row that has the type "greeting".

            >>> get_ids({"type": "nickname,quip", "by": "Varric"})
            # Any row by "Varric" that has the type "nickname" or "quip".
            [23, 24, 25, 34, 37, 41, 42, 43]
        """
        ids = []
        table = clean(table)
        clause = ""
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.row_factory = lambda cursor, row: row[0]  # Gets first element for fetchall()
            c = connection.cursor()

            if conditions:
                clause = "WHERE ("
                clause_list = [clause,]
                substitutes = []
                cat_count = 1
                header_count = 1

                ## TODO: Add ability to specify comparison operator (e.g. =, <, LIKE, etc.)
                for con in conditions:
                    if 1 < header_count:
                        clause_list.append(" AND (")

                    sub_count = 1
                    subconditions = conditions[con].split(splitter)
                    for sub in subconditions:
                        if 1 < sub_count:
                            clause_list.append(" OR ")
                        
                        clause_list.append(f"{clean(con)}=?")
                        substitutes.append(sub)
                        sub_count += 2
                        
                    clause_list.append(")")
                    header_count += 2
                    cat_count = 1

                clause = "".join(clause_list)

                statement = f"SELECT id FROM {table} {clause}"
                logger.debug(f"(get_ids) Substitutes: {substitutes}")
                logger.debug(f"(get_ids) SQLite statement: {statement}")

                c.execute(statement, substitutes)
            else:
                c.execute(f"SELECT id FROM {table}")

            ids = c.fetchall()

        return ids

    def insert(self, table, values, headers=None):
        """ Inserts records into the table.

        Args:
            table(str): Name of table.
            values(list): List of tuples containing the values to insert.
                Each tuple represents one row.
            
        """
        table = clean(table)
        if headers:
            headers = [clean(h) for h in headers]

        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

    def random_line(self, header, table, conditions=None, splitter=","):
        """ Chooses a random line from the table under the header.

        Args:
            header(unicode): The header of the random line's column.
            table(unicode): Name of the table to look into.
            conditions(dict, optional): Categories to filter the line by:
                {"header of categories 1": "category1,category2",
                 "header of category 2": "category3"}
                Multiple categories under a single header are separated with a comma.
            splitter(unicode, optional): What separates multiple categories
                (default is a comma).

        Returns:
            line(unicode): A random line from the database.

        Raises:
            OperationalError: If header or table doesn't exist.
            TypeError: If category is neither None nor a dictionary.

        Examples:
            >>> random_line("line", {"type": "greeting"})
            Hello.
        """
        header = clean(header)
        table = clean(table)
        line = ""
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

            if conditions:
                ids = self.get_ids(table, conditions, splitter)
                if ids:
                    line = random.choice(ids)
                    line = self.get_field(line, header, table)
            else:
                c.execute(f"SELECT {header} FROM {table} ORDER BY Random() LIMIT 1")  # TODO: Take categories into account.
                line = c.fetchone()[0]

        return line
