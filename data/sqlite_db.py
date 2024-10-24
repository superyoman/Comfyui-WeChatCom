import sqlite3
from sqlite3 import Error

global cot_db
cot_db = "db/wx.db"

def create_connection(db_file):
    """ 创建一个数据库连接到 SQLite 数据库指定的 db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # print("Connection is established: Database is created in memory")
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ 使用提供的 conn 连接和 create_table_sql 创建表 """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def insert_data(conn, table_name, task):
    """ 插入数据到指定的表中 """
    try:
        c = conn.cursor()

        # 获取 task 字典的键和值
        # print(task)
        columns = ', '.join(task.keys())
        placeholders = ', '.join(['?' for _ in task])
        values = tuple(task.values())

        # 构建 SQL 语句
        sql = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'

        # 执行 SQL 语句
        c.execute(sql, values)
        conn.commit()
        # print(f"数据成功插入到 {table_name} 表中")
    except Error as e:
        # print(f"插入数据时发生错误: {e}")
        raise


def query_data(table,sql_where = None):
    """ 查询并打印 tasks 表中的所有数据 """
    try:
        conn = sqlite3.connect(cot_db)
        c = conn.cursor()
        c.execute(f"SELECT * FROM {table} {sql_where}")
        rows = c.fetchall()
        return rows
    except Error as e:
        print(e)
        return []


def query_data_dict(table, sql_where=None):
    """ 查询并返回指定表中的所有数据，以字典形式输出，包含字段名 """
    try:
        conn = sqlite3.connect(cot_db)
        c = conn.cursor()

        # 构建 SQL 查询
        query = f"SELECT * FROM {table}"
        if sql_where:
            query += f" {sql_where}"

        c.execute(query)

        # 获取列名
        columns = [column[0] for column in c.description]

        # 获取所有行并转换为字典
        rows = c.fetchall()

        # 如果没有行，返回空字典
        if not rows:
            return {}

        # 将每一行转换为字典
        result = [dict(zip(columns, row)) for row in rows]

        return result
    except sqlite3.Error as e:
        print(e)
        return {}
    finally:
        if conn:
            conn.close()


def update_table(table_name, data, id_field, id_value):
    """
    根据 id_field 和 id_value 更新指定表的数据。
    如果记录不存在则插入新记录。

    :param table_name: 数据库表名
    :param data: 包含要更新或插入的数据的字典
    :param id_field: 用于检查记录是否存在的字段名
    :param id_value: 用于检查记录是否存在的字段值
    :return: True 如果插入或更新成功，False 如果发生错误
    """
    # 构建 SQL 查询
    sql_check = f'SELECT COUNT(*) FROM {table_name} WHERE {id_field} = ?'

    # 动态构建插入或更新的 SQL 语句
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    sql_insert = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'

    try:
        conn = sqlite3.connect(cot_db)  # 替换为您的数据库路径
        cursor = conn.cursor()

        # 检查记录是否已存在
        cursor.execute(sql_check, (id_value,))
        if cursor.fetchone()[0] > 0:
            print(f"Record with {id_field} = '{id_value}' already exists. Updating.")
            # 如果存在，则更新记录
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            sql_update = f'UPDATE {table_name} SET {set_clause} WHERE {id_field} = ?'
            cursor.execute(sql_update, list(data.values()) + [id_value])
        else:
            # 如果不存在，则插入数据
            cursor.execute(sql_insert, list(data.values()))

        conn.commit()
        print(f"Record with {id_field} = '{id_value}' processed successfully.")
        return True

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def query_data_by_username(conn, table_name, username):
    """ 根据提供的 username 查询指定表中的对应数据 """
    try:
        c = conn.cursor()
        # 使用参数化查询以防止 SQL 注入
        c.execute(f"SELECT * FROM {table_name} WHERE username=?", (username,))
        rows = c.fetchall()
        if rows:
            # 获取列名
            column_names = [description[0] for description in c.description]
            # 将结果转换为字典列表
            result = [dict(zip(column_names, row)) for row in rows]
            return result
        else:
            print(f"No data found for username '{username}' in table '{table_name}'")
            return None
    except Error as e:
        print(f"Error querying data: {e}")
        raise

info_db = {
    "at_record":[""" 
                chat_id text PRIMARY KEY,
                chat text,
                room_id text,
                sender_id text,
                modified_time integer,
                completed text                        
                """,
               ["chat_id","chat","room_id","sender_id","modified_time","completed"]],

    "config":[""" 
            id text,
            wx_type text                                  
             """,
            ["wx_id","wx_type"]],

    "reply_record": [""" 
            chat_id text,
            chat text,
            room_id text,
            receiver_id text,
            modified_time integer,
            completed text,
            asset text                       
            """,
        ["chat_id", "chat", "room_id", "receiver_id", "modified_time", "completed", "asset"]],

    "mission_record": [""" 
        chat_id text,
        chat text,
        room_id text,
        receiver_id text,
        modified_time integer,
        completed text,
        mission text,
        result text                  
        """,
        ["chat_id", "chat", "room_id", "receiver_id", "modified_time", "completed", "mission", "result"]],

    }

def preperation(table_name = "config"):
    # 创建一个数据库连接
    #Defalut DB name:cot
    conn = create_connection(cot_db)
    # 创建表
    if conn is not None:
        try:
            create_table(conn, f'''CREATE TABLE IF NOT EXISTS {table_name} ({info_db[table_name][0]});''')
        except Exception as ex:
            print(ex)
    else:
        print("Error! cannot create the database connection.")
    return conn

def add_data(table_name = "",data = dict):
    conn = preperation(table_name)
    try:
        # 插入数据
        with conn:
            insert_data(conn, table_name, data)
        # 关闭连接
        conn.close()
        return True

    except sqlite3.IntegrityError as ex:
        print(ex)
        raise


def update_data(table_name, data, username_key='username'):
    """根据提供的 username 更新对应的 row"""
    try:
        conn = preperation(table_name)
        c = conn.cursor()

        # 从数据中移除 username，因为它是我们的 WHERE 条件
        username = data.pop(username_key, None)
        print(username)
        if username is None:
            raise ValueError(f"'{username_key}' not found in the data.")

        # 构建 SET 子句
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])

        # 构建完整的 SQL 语句
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {username_key} = ?"

        # 准备参数：所有的值加上 username
        params = list(data.values()) + [username]

        # 执行 SQL 语句
        c.execute(sql, params)
        conn.commit()

        if c.rowcount == 0:
            print(f"No rows were updated for username: {username}")
            return False

        print(f"Successfully updated {c.rowcount} row(s) for username: {username}")
        return True

    except Error as e:
        print(f"Error updating data: {e}")
        return False
    except ValueError as e:
        print(f"Value error: {e}")
        return False
    finally:
        # 确保我们不会意外修改原始数据
        data[username_key] = username


if __name__ == '__main__':
    # add_data(table_name = "config", data = {"id": "adadadda", "wx_type":"chatroom"})
    q = query_data(table="at_record", sql_where = "where completed = 'init' ")
    print(q)