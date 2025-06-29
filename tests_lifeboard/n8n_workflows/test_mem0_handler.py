import unittest
import json
import sys
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Import the module to be tested using its full path from the project root
import backend.n8n_scripts.mem0_handler as mem0_handler_module

class TestMem0Handler(unittest.TestCase):

    def setUp(self):
        # Create a mock for the Mem0 SDK instance
        self.mock_mem0_sdk_instance = MagicMock()
        self.mock_mem0_sdk_instance.add = MagicMock(return_value={"id": "mem123", "status": "success"})
        self.mock_mem0_sdk_instance.search = MagicMock(return_value=[{"id": "mem456", "text": "found memory"}])

        # Patch Memory.from_config to return our mock SDK instance
        self.patch_Memory_from_config = patch.object(mem0_handler_module.Memory, 'from_config', return_value=self.mock_mem0_sdk_instance)
        self.MockMemoryFromConfig = self.patch_Memory_from_config.start()
        mem0_handler_module.mem0_instance = self.mock_mem0_sdk_instance # Pre-set global instance

        # Mock ollama.Client for summarize and chat response functions
        self.patch_ollama_client = patch('ollama.Client')
        self.MockOllamaClient = self.patch_ollama_client.start()
        self.mock_ollama_instance = self.MockOllamaClient.return_value
        self.mock_ollama_instance.chat = MagicMock(return_value={'message': {'content': 'Mocked LLM response.'}})

        # Patch sys.argv for main() tests
        self.patch_argv = patch.object(sys, 'argv', [])
        self.mock_argv = self.patch_argv.start()

        # Patch sys.stdout for main() tests
        self.patch_stdout = patch('sys.stdout', new_callable=MagicMock)
        self.mock_stdout = self.patch_stdout.start()
        self.mock_stdout.write = MagicMock() # Ensure 'write' is a MagicMock

        # Patch sys.stderr for main() error tests
        self.patch_stderr = patch('sys.stderr', new_callable=MagicMock)
        self.mock_stderr = self.patch_stderr.start()
        self.mock_stderr.write = MagicMock() # Ensure 'write' is a MagicMock


    def tearDown(self):
        self.patch_Memory_from_config.stop()
        self.patch_ollama_client.stop()
        self.patch_argv.stop()
        self.patch_stdout.stop()
        self.patch_stderr.stop()
        # Reset the global instance after each test to ensure test isolation
        mem0_handler_module.mem0_instance = None


    @patch.object(mem0_handler_module.Memory, 'from_config')
    def test_get_mem0_instance_initialization(self, mock_Memory_from_config):
        # This test specifically tests the lazy initialization of mem0_instance,
        # so we need to ensure it's None before the call.
        mem0_handler_module.mem0_instance = None

        # The mock_Memory_from_config is already set up by the class-level patch if we didn't stop it
        # or if we re-patch it here. For clarity, using the one passed to the method.
        mock_sdk_instance_local = MagicMock()
        mock_Memory_from_config.return_value = mock_sdk_instance_local

        instance = mem0_handler_module.get_mem0_instance()
        self.assertIsNotNone(instance)
        mock_Memory_from_config.assert_called_once_with(mem0_handler_module.MEM0_CONFIG)
        self.assertEqual(instance, mock_sdk_instance_local)

        # Test singleton behavior
        instance2 = mem0_handler_module.get_mem0_instance()
        self.assertEqual(instance, instance2)
        mock_Memory_from_config.assert_called_once() # Still called only once


    def test_add_memory_success(self):
        data_to_add = {"key": "value"}
        user_id = "test_user"
        metadata = {"source": "test_source"}

        result = mem0_handler_module.add_memory(data_to_add, user_id, metadata)

        self.mock_mem0_sdk_instance.add.assert_called_once_with(
            json.dumps(data_to_add), user_id=user_id, metadata=metadata
        )
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)

    def test_add_memory_string_data(self):
        data_to_add = "This is a string memory"
        user_id = "test_user_str"

        result = mem0_handler_module.add_memory(data_to_add, user_id)

        self.mock_mem0_sdk_instance.add.assert_called_once_with(
            data_to_add, user_id=user_id, metadata=None
        )
        self.assertEqual(result["status"], "success")

    @patch.object(mem0_handler_module, 'get_mem0_instance') # Mock the instance getter
    def test_add_memory_sdk_exception(self, mock_get_instance):
        mock_instance = mock_get_instance.return_value
        mock_instance.add.side_effect = Exception("SDK Error")

        result = mem0_handler_module.add_memory("data", "user")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "SDK Error")

    def test_search_memories_success(self):
        query = "test query"
        user_id = "test_user"

        result = mem0_handler_module.search_memories(query, user_id)

        self.mock_mem0_sdk_instance.search.assert_called_once_with(query, user_id=user_id)
        self.assertEqual(result["status"], "success")
        self.assertIn("results", result)

    @patch.object(mem0_handler_module, 'get_mem0_instance')
    def test_search_memories_sdk_exception(self, mock_get_instance):
        mock_instance = mock_get_instance.return_value
        mock_instance.search.side_effect = Exception("Search SDK Error")

        result = mem0_handler_module.search_memories("query", "user")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Search SDK Error")

    # Tests for main() function
    def test_main_add_action(self):
        payload = {"user_id": "main_user", "data": "main data", "metadata": {"source": "main_test"}}
        self.mock_argv[:] = ['mem0_handler.py', 'add', json.dumps(payload)]

        mem0_handler_module.main()

        # If payload["data"] is a string, it's passed as is.
        expected_data_arg = payload["data"] if isinstance(payload["data"], str) else json.dumps(payload["data"])
        self.mock_mem0_sdk_instance.add.assert_called_once_with(
            expected_data_arg, user_id=payload["user_id"], metadata=payload["metadata"]
        )
        # Check stdout for success message
        # Concatenate all arguments from all calls to mock_stdout.write
        output = "".join(arg for call_args in self.mock_stdout.write.call_args_list for arg in call_args[0])
        self.assertIn('"status": "success"', output)

    def test_main_search_action(self):
        payload = {"user_id": "main_user_search", "query": "main query"}
        self.mock_argv[:] = ['mem0_handler.py', 'search', json.dumps(payload)]

        mem0_handler_module.main()

        self.mock_mem0_sdk_instance.search.assert_called_once_with(
            payload["query"], user_id=payload["user_id"]
        )
        output = "".join(call_args[0][0] for call_args in self.mock_stdout.write.call_args_list)
        self.assertIn('"status": "success"', output)

    def test_main_invalid_action(self):
        self.mock_argv[:] = ['mem0_handler.py', 'unknown_action', '{}']
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn('"status": "error"', err_output)
        self.assertIn("Unknown action: unknown_action", err_output)

    def test_main_missing_args(self):
        self.mock_argv[:] = ['mem0_handler.py', 'add'] # Missing payload
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Usage: python mem0_handler.py <action> <payload_json_string>", err_output)

    def test_main_invalid_json_payload(self):
        self.mock_argv[:] = ['mem0_handler.py', 'add', 'this is not json']
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Invalid JSON payload", err_output)

    def test_main_add_action_missing_data(self):
        payload = {"user_id": "main_user"} # Missing "data"
        self.mock_argv[:] = ['mem0_handler.py', 'add', json.dumps(payload)]
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Missing 'data' in payload for add action", err_output)

    def test_main_search_action_missing_query(self):
        payload = {"user_id": "main_user"} # Missing "query"
        self.mock_argv[:] = ['mem0_handler.py', 'search', json.dumps(payload)]
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Missing 'query' in payload for search action", err_output)

    # Tests for summarize_text_ollama
    def test_summarize_text_ollama_success(self):
        self.mock_ollama_instance.chat.return_value = {'message': {'content': ' Test summary. '}}
        result = mem0_handler_module.summarize_text_ollama("Some text", "Prompt:")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"], "Test summary.")
        self.mock_ollama_instance.chat.assert_called_once()
        # You could add more specific assertions about the prompt passed to ollama

    def test_summarize_text_ollama_api_error(self):
        self.mock_ollama_instance.chat.side_effect = Exception("Ollama API error")
        result = mem0_handler_module.summarize_text_ollama("Some text", "Prompt:")
        self.assertEqual(result["status"], "error")
        self.assertIn("Ollama summarization error: Ollama API error", result["message"])

    # Tests for llm_chat_response_ollama
    def test_llm_chat_response_ollama_success(self):
        self.mock_ollama_instance.chat.return_value = {'message': {'content': ' Test chat reply. '}}
        result = mem0_handler_module.llm_chat_response_ollama("User query", ["context mem1"], "Chat prompt:")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["reply"], "Test chat reply.")
        self.mock_ollama_instance.chat.assert_called_once()
        # Assertions on the prompt structure could be added

    def test_llm_chat_response_ollama_api_error(self):
        self.mock_ollama_instance.chat.side_effect = Exception("Ollama Chat API error")
        result = mem0_handler_module.llm_chat_response_ollama("User query", [], "Chat prompt:")
        self.assertEqual(result["status"], "error")
        self.assertIn("Ollama chat response error: Ollama Chat API error", result["message"])

    # Tests for new main() actions
    def test_main_summarize_action(self):
        payload = {"text": "long text to summarize", "prompt": "Summarize this:"}
        self.mock_argv[:] = ['mem0_handler.py', 'summarize', json.dumps(payload)]
        self.mock_ollama_instance.chat.return_value = {'message': {'content': ' Summarized. '}}

        mem0_handler_module.main()

        self.mock_ollama_instance.chat.assert_called_once()
        output = "".join(arg for call_args in self.mock_stdout.write.call_args_list for arg in call_args[0])
        self.assertIn('"status": "success"', output)
        self.assertIn('"summary": "Summarized."', output)

    def test_main_summarize_action_missing_text(self):
        payload = {} # Missing "text"
        self.mock_argv[:] = ['mem0_handler.py', 'summarize', json.dumps(payload)]
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Missing 'text' in payload for summarize action", err_output)

    def test_main_generate_chat_response_action(self):
        payload = {"query": "Hello?", "context": ["memory1"], "prompt_template": "Respond:"}
        self.mock_argv[:] = ['mem0_handler.py', 'generate_chat_response', json.dumps(payload)]
        self.mock_ollama_instance.chat.return_value = {'message': {'content': ' Hi there. '}}

        mem0_handler_module.main()

        self.mock_ollama_instance.chat.assert_called_once()
        output = "".join(arg for call_args in self.mock_stdout.write.call_args_list for arg in call_args[0])
        self.assertIn('"status": "success"', output)
        self.assertIn('"reply": "Hi there."', output)

    def test_main_generate_chat_response_missing_query(self):
        payload = {"context": ["memory1"]} # Missing "query"
        self.mock_argv[:] = ['mem0_handler.py', 'generate_chat_response', json.dumps(payload)]
        with self.assertRaises(SystemExit):
            mem0_handler_module.main()
        err_output = "".join(arg for call_args in self.mock_stderr.write.call_args_list for arg in call_args[0])
        self.assertIn("Missing 'query' in payload for generate_chat_response action", err_output)


if __name__ == '__main__':
    unittest.main()
