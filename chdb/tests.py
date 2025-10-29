"""ClickHouse 数据库集成测试."""

import threading
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase

from chdb.clickhousedb import ClickHouseDB, command, insert, query


class ClickHouseDBTests(TestCase):
    """ClickHouse 数据库封装类测试."""

    def setUp(self):
        """每个测试前重置连接."""
        ClickHouseDB.reset_connection()

    def tearDown(self):
        """每个测试后重置连接."""
        ClickHouseDB.reset_connection()

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_get_instance_creates_singleton(self, mock_get_client):
        """测试 get_instance 创建单例."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        instance1 = ClickHouseDB.get_instance()
        instance2 = ClickHouseDB.get_instance()

        # 验证返回相同实例
        self.assertIs(instance1, instance2)
        # 验证只调用一次 get_client
        mock_get_client.assert_called_once()

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_get_instance_thread_safety(self, mock_get_client):
        """测试 get_instance 线程安全性."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        instances = []
        errors = []

        def create_instance():
            try:
                instance = ClickHouseDB.get_instance()
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        # 创建多个线程并发获取实例
        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证没有错误发生
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # 验证所有实例都相同
        self.assertEqual(len(instances), 10)
        self.assertTrue(all(inst is instances[0] for inst in instances))

        # 验证只调用一次 get_client
        mock_get_client.assert_called_once()

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_reset_connection(self, mock_get_client):
        """测试重置连接."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # 创建实例
        instance1 = ClickHouseDB.get_instance()
        self.assertIsNotNone(instance1)

        # 重置连接
        ClickHouseDB.reset_connection()

        # 验证 close 被调用
        mock_client.close.assert_called_once()

        # 重新获取应该创建新实例
        mock_get_client.reset_mock()
        mock_client2 = Mock()
        mock_get_client.return_value = mock_client2

        instance2 = ClickHouseDB.get_instance()

        # 验证重新调用了 get_client
        mock_get_client.assert_called_once()
        # 验证获取了新实例
        self.assertEqual(instance2, mock_client2)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_reset_connection_thread_safety(self, mock_get_client):
        """测试 reset_connection 线程安全性."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # 先创建实例
        ClickHouseDB.get_instance()

        errors = []

        def reset_instance():
            try:
                ClickHouseDB.reset_connection()
            except Exception as e:
                errors.append(e)

        # 多线程并发重置
        threads = [threading.Thread(target=reset_instance) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_query(self, mock_get_client):
        """测试查询方法."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.query.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = ClickHouseDB.query("SELECT 1")

        mock_client.query.assert_called_once_with(
            "SELECT 1", parameters=None, settings=None
        )
        self.assertEqual(result, mock_result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_query_with_parameters(self, mock_get_client):
        """测试带参数的查询."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.query.return_value = mock_result
        mock_get_client.return_value = mock_client

        params = {"id": 1}
        result = ClickHouseDB.query("SELECT * FROM test WHERE id = {id:UInt32}", params)

        mock_client.query.assert_called_once_with(
            "SELECT * FROM test WHERE id = {id:UInt32}",
            parameters=params,
            settings=None,
        )
        self.assertEqual(result, mock_result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_command(self, mock_get_client):
        """测试命令方法."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.command.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = ClickHouseDB.command("CREATE TABLE test (id UInt32)")

        mock_client.command.assert_called_once_with(
            "CREATE TABLE test (id UInt32)", parameters=None, settings=None
        )
        self.assertEqual(result, mock_result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_insert(self, mock_get_client):
        """测试插入方法."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        data = [[1, "test"], [2, "test2"]]
        columns = ["id", "name"]

        ClickHouseDB.insert("test_table", data, columns)

        mock_client.insert.assert_called_once_with(
            "test_table", data, column_names=columns, settings=None
        )

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_query_df(self, mock_get_client):
        """测试 DataFrame 查询."""
        mock_client = Mock()
        mock_df = MagicMock()
        mock_client.query_df.return_value = mock_df
        mock_get_client.return_value = mock_client

        result = ClickHouseDB.query_df("SELECT 1")

        mock_client.query_df.assert_called_once_with(
            "SELECT 1", parameters=None, settings=None
        )
        self.assertEqual(result, mock_df)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_query_arrow(self, mock_get_client):
        """测试 Arrow 查询."""
        mock_client = Mock()
        mock_table = Mock()
        mock_client.query_arrow.return_value = mock_table
        mock_get_client.return_value = mock_client

        result = ClickHouseDB.query_arrow("SELECT 1")

        mock_client.query_arrow.assert_called_once_with(
            "SELECT 1", parameters=None, settings=None
        )
        self.assertEqual(result, mock_table)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_ping_success(self, mock_get_client):
        """测试 ping 成功."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_get_client.return_value = mock_client

        # 先创建实例
        ClickHouseDB.get_instance()

        result = ClickHouseDB.ping()

        self.assertTrue(result)
        mock_client.ping.assert_called_once()

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_ping_connection_fails(self, mock_get_client):
        """测试 ping 连接失败."""
        # 模拟连接创建失败
        mock_get_client.side_effect = Exception("Connection failed")

        result = ClickHouseDB.ping()
        self.assertFalse(result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_ping_exception(self, mock_get_client):
        """测试 ping 异常."""
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection lost")
        mock_get_client.return_value = mock_client

        # 先创建实例
        ClickHouseDB.get_instance()

        result = ClickHouseDB.ping()

        self.assertFalse(result)


class ConvenienceFunctionsTests(TestCase):
    """便捷函数测试."""

    def setUp(self):
        """每个测试前重置连接."""
        ClickHouseDB.reset_connection()

    def tearDown(self):
        """每个测试后重置连接."""
        ClickHouseDB.reset_connection()

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_query_function(self, mock_get_client):
        """测试 query 便捷函数."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.query.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = query("SELECT 1")

        self.assertEqual(result, mock_result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_command_function(self, mock_get_client):
        """测试 command 便捷函数."""
        mock_client = Mock()
        mock_result = Mock()
        mock_client.command.return_value = mock_result
        mock_get_client.return_value = mock_client

        result = command("SHOW TABLES")

        self.assertEqual(result, mock_result)

    @patch("chdb.clickhousedb.clickhouse_connect.get_client")
    def test_insert_function(self, mock_get_client):
        """测试 insert 便捷函数."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        data = [[1, "test"]]
        insert("test_table", data, ["id", "name"])

        mock_client.insert.assert_called_once()
