# -*- coding: utf-8 -*-
import logging
import random
import sqlite3
from contextlib import closing

logger = logging.getLogger(__name__)

def clean(line):
    """Strip a string of non-alphanumerics (except underscores).
    Can use to clean strings before using them in a database query.

    Args:
        line (str): String to clean.

    Returns:
        line (str): A string safe to use in a database query.

    Examples:
        >>> clean("Robert'); DROP TABLE Students;")
        RobertDROPTABLEStudents
        
    """
    return "".join(char for char in line if (char.isalnum() or "_" == char))


class TableColumn(object):
    """Represents a column in a database table.

    Args:
        name (str): Name of the column.
        datatype (str): Data type the column contains.

    Kwargs:
        primary_key (bool, optional): Specifies if the column is the primary
            key or not. Defaults to False.
        allow_null (bool, optional): Whether fields may have null values or
            not. Defaults to True.
        unique (bool, optional): Specifies if column fields must be unique.
            Defaults to False.

    """

    def __init__(self, name, datatype, **constraints):
        self.name = clean(name)
        self.datatype = datatype
        self.primary_key = constraints.get("primary_key", False)
        self.allow_null = constraints.get("allow_null", True)
        self.unique = constraints.get("unique", False)
    

class Database(object):
    """For reading and writing records in a SQLite database.

    Args:
        dbFile (str): The filepath of the database.
        
    """
    
    def __init__(self, db_file):
        self.db = db_file

    def _get_conditions(self, conditions, delimiter=","):
        """Returns a WHERE clause according to given conditions.

        Args:
            conditions (dict):

        Returns:
            clause (tuple): The string statement and the substitutes for ? placeholders.
        """
        clause = "WHERE ("
        clause_list = [clause,]
        substitutes = []
        cat_count = 1
        column_count = 1

        ## TODO: Add ability to specify comparison operator (e.g. =, <, LIKE, etc.)
        for con in conditions:
            if 1 < column_count:
                clause_list.append(" AND (")

            sub_count = 1
            subconditions = conditions[con].split(delimiter)
            for sub in subconditions:
                if 1 < sub_count:
                    clause_list.append(" OR ")
                
                clause_list.append(f"{clean(con)}=?")
                substitutes.append(sub)
                sub_count += 2
                
            clause_list.append(")")
            column_count += 2
            cat_count = 1

        clause = "".join(clause_list)

        return (clause, substitutes)

    def execute(self, statement, substitutes=None):
        """Executes a statement.

        Args:
            statement (str): Statement to execute.
            substitutes (list): Values to substitute placeholders in statement.

        """
        connection = sqlite3.connect(self.db)
        
        with closing(connection) as connection:
            c = connection.cursor()
            
            if substitutes:
                c.execute(statement, substitutes)
            else:
                c.execute(statement)

            connection.commit()

    def create_table(self, name, columns):
        """Creates a table.

        Args:
            name (str): Name of table.
            columns (list): List of TableColumns.

        """
        connection = sqlite3.connect(self.db)
        name = clean(name)
        statement = [f"CREATE TABLE `{name}`(",]
        
        with closing(connection) as connection:
            i = 1
            for col in columns:
                pk = " PRIMARY KEY" if col.primary_key else ""
                null = " NOT NULL" if not col.allow_null else ""
                unique = " UNIQUE" if col.unique else ""

                if len(columns) > i:
                    column = f"`{col.name}` {col.datatype}{pk}{null}{unique},"
                else:
                    column = f"`{col.name}` {col.datatype}{pk}{null}{unique}"

                statement.append(column)
                i += 1

            statement.append(");")
            statement = "\n".join(statement)
            connection.execute(statement)

    def rename_table(self, table, new_name):
        """Renames a table."""
        table = clean(table)
        new_name = clean(new_name)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.execute(f"ALTER TABLE {table} RENAME TO {new_name}")

    def add_column(self, table, column):
        """Adds a column to a table."""
        connection = sqlite3.connect(self.db)
        table = clean(table)

        with closing(connection) as connection:
            null = " NOT NULL" if not col.allow_null else ""
            unique = " UNIQUE" if col.unique else ""                
            col = f"`{column.name}` {column.datatype}{null}{unique}"
            
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {col}")

    def drop_table(self, table):
        """Deletes a table."""
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.execute(f"DROP TABLE IF EXISTS {table}")

    def insert(self, table, values, columns=None):
        """Inserts records into the table.

        Args:
            table (str): Name of table.
            values (list): List of tuples containing the values to insert.
                Each tuple represents one row.
            columns (list, optional): List of column names corresponding to
                the values being inserted.
            
        """
        table = clean(table)
        if columns:
            columns = [clean(h) for h in columns]

        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

            cols = ""
            if columns:
                cols = ",".join(columns)
                cols = f"({cols})"

            for row in values:
                placeholders = ",".join(["?" for field in row])
                statement = f"INSERT INTO {table}{cols} VALUES({placeholders})"
                c.execute(statement, row)

            connection.commit()

    def update(self, table, new_values, conditions=None):
        """Updates records on a table.

        Args:
            table (str): Name of the table.
            new_values (dict): The new values in each column. e.g.
                {"column1": "new1", "column2": "new2"}
            conditions (dict, optional): Categories to filter the update by:
                {"column of categories 1": "category1,category2",
                 "column of category 2": "category3"}
                Multiple categories under a single column are separated with a comma.

        """
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()
            
            to_update = []
            substitutes = []
            for column in new_values:
                to_update.append(f"{column} = ?")
                substitutes.append(new_values[column])

            to_update = ", ".join(to_update)

            where = ""
            if conditions:
                where, where_subs = self._get_conditions(conditions)
                substitutes = [*substitutes, *where_subs]

            statement = f"UPDATE {table} SET {to_update} {where}"
            print(statement, substitutes)
            c.execute(statement, substitutes)

            connection.commit()

    def delete(self, table, conditions=None):
        """Deletes records from a table."""
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()
            
            if conditions:
                where, substitutes = self._get_conditions(conditions)
                statement = f"DELETE FROM {table} {conditions}"
                c.execute(statement, substitutes)
            else:
                c.execute(f"DELETE FROM {table}")

            connection.commit()

    def create_index(self, name, table, columns, unique=False):
        """Create an index for a table.

        Args:
            name (str): Name of index.
            table (str): Table to index.
            columns (list): List of columns to index.
            unique (bool, optional): Specify if index is unique or not.

        """
        name = clean(name)
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            cols = ",".join([clean(c) for c in columns])
            u = "UNIQUE " if unique else ""
            statement = f"CREATE {u}INDEX IF NOT EXISTS {name} ON {table}({cols})"

            connection.execute(statement)

    def drop_index(self, name):
        """Deletes an index."""
        name = clean(name)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.execute(f"DROP INDEX IF EXISTS {name}")

    def get_column(self, column, table, maximum=None):
        """Gets fields under a column.

        Args:
            column (str): Name of column.
            table (str): Name of table.
            maximum (int, optional): Maximum amount of fields to fetch.

        Returns:
            fields (list): List of fields under column.
            
        """
        fields = []
        table = clean(table)
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.row_factory = lambda cursor, row: row[0]
            c = connection.cursor()
            if maximum:
                c.execute(f"SELECT {column} FROM {table} LIMIT ?", [maximum])
            else:
                c.execute(f"SELECT {column} FROM {table}")
            fields = c.fetchall()
        
        return fields

    def get_field(self, field_id, column, table):
        """Gets the field under the specified column by its primary key value.

        Args:
            field_id (int, str): Unique ID of line the field is in.
            column (str): Column of the field to fetch.
            table (str): Name of table to look into.

        Returns:
            The desired field, or None if the lookup failed.

        Raises:
            TypeError: If field_id doesn't exist in the table.
        
        Examples:
            >>> get_field(123, "firstname", "kings")
            Adgar
            
        """
        column = clean(column)
        table = clean(table)
        field = None
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

            statement = f"SELECT {column} FROM {table} WHERE id=?"
            logger.debug(statement)
            c.execute(statement, [field_id])

            try:
                field = c.fetchone()[0]
            except TypeError:
                logger.exception(f"ID '{field_id}' was not in table '{table}'")
        
        return field

    def get_ids(self, table, column_id="id", conditions=None, delimiter=","):
        """Gets the IDs that fit within the specified conditions.

        Gets all IDs if conditions is None.

        Args:
            table (str): Name of table to look into.
            conditions (dict, optional): Categories you want to filter the line by:
                {"column of categories 1": "category1,category2",
                 "column of category 2": "category3"}
                Multiple categories under a single column are separated with a comma.

        Returns:
            ids (list): List of IDs that match the categories.

        Raises:
            OperationalError: If table or column doesn't exist.
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
        column_id = clean(column_id)
        clause = ""
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            connection.row_factory = lambda cursor, row: row[0]  # Gets first element for fetchall()
            c = connection.cursor()

            if conditions:
                clause, substitutes = self._get_conditions(conditions)

                statement = f"SELECT \"{column_id}\" FROM \"{table}\" {clause}"
                logger.debug(f"(get_ids) SQLite statement: {statement}")
                logger.debug(f"(get_ids) Substitutes: {substitutes}")

                c.execute(statement, substitutes)
            else:
                c.execute(f"SELECT \"{column_id}\" FROM \"{table}\"")

            ids = c.fetchall()

        return ids

    def random_line(self, column, table, column_id="id", conditions=None, delimiter=","):
        """Chooses a random line from the table under the column.

        Args:
            column (str): The name of the random line's column.
            table (str): Name of the table to look into.
            column_id (str, optional): Name of the id column. Default is "id".
            conditions (dict, optional): Categories to filter the line by:
                {"column of categories 1": "category1,category2",
                 "column of category 2": "category3"}
                Multiple categories under a single column are separated with a comma.
            delimiter (str, optional): What separates multiple categories
                (default is a comma).

        Returns:
            line(str): A random line from the database.

        Raises:
            OperationalError: If column or table doesn't exist.
            TypeError: If category is neither None nor a dictionary.

        Examples:
            >>> random_line("line", {"type": "greeting"})
            Hello.
            
        """
        column = clean(column)
        table = clean(table)
        column_id = clean(column_id)
        line = ""
        
        connection = sqlite3.connect(self.db)

        with closing(connection) as connection:
            c = connection.cursor()

            if conditions:
                ids = self.get_ids(table, column_id, conditions, delimiter)
                if ids:
                    line = random.choice(ids)
                    line = self.get_field(line, column, table)
            else:
                c.execute(f"SELECT {column} FROM {table} ORDER BY Random() LIMIT 1")
                line = c.fetchone()[0]

        return line
