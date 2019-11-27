import asyncio
import re

import asynctest
import httpx
import trio
from httpx.concurrency.trio import TrioBackend

import respx


class HTTPXMockTestCase(asynctest.TestCase):
    def await_coroutine(self, coroutine):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coroutine)

    @respx.mock
    def test_sync_global_decorator(self):
        self.assertEqual(respx.stats.call_count, 0)

        request = respx.get("https://foo/bar/", status_code=202)
        response = self.await_coroutine(httpx.get("https://foo/bar/"))

        self.assertTrue(request.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(respx.stats.call_count, 1)

    @respx.mock
    async def test_async_global_decorator(self):
        self.assertEqual(respx.stats.call_count, 0)

        request = respx.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")

        self.assertTrue(request.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(respx.stats.call_count, 1)

    @respx.mock()
    def test_sync_local_decorator(self, httpx_mock):
        self.assertEqual(respx.stats.call_count, 0)
        self.assertEqual(httpx_mock.stats.call_count, 0)

        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = self.await_coroutine(httpx.get("https://foo/bar/"))

        self.assertTrue(request.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(respx.stats.call_count, 0)
        self.assertEqual(httpx_mock.stats.call_count, 1)

    @respx.mock()
    async def test_async_local_decorator(self, httpx_mock):
        self.assertEqual(respx.stats.call_count, 0)
        self.assertEqual(httpx_mock.stats.call_count, 0)

        request = httpx_mock.get("https://foo/bar/", status_code=202)
        response = await httpx.get("https://foo/bar/")

        self.assertTrue(request.called)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(respx.stats.call_count, 0)
        self.assertEqual(httpx_mock.stats.call_count, 1)

    async def test_sync_global_contextmanager(self):
        self.assertEqual(respx.stats.call_count, 0)

        with respx.mock:
            request = respx.get("https://foo/bar/", status_code=202)
            response = await httpx.get("https://foo/bar/")

            self.assertTrue(request.called)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(respx.stats.call_count, 1)

        self.assertEqual(respx.stats.call_count, 0)

    async def test_async_global_contextmanager(self):
        self.assertEqual(respx.stats.call_count, 0)

        async with respx.mock:
            request = respx.get("https://foo/bar/", status_code=202)
            response = await httpx.get("https://foo/bar/")

            self.assertTrue(request.called)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(respx.stats.call_count, 1)

        self.assertEqual(respx.stats.call_count, 0)

    async def test_sync_local_contextmanager(self):
        with respx.mock() as httpx_mock:
            self.assertEqual(respx.stats.call_count, 0)
            self.assertEqual(httpx_mock.stats.call_count, 0)

            request = httpx_mock.get("https://foo/bar/", status_code=202)
            response = await httpx.get("https://foo/bar/")

            self.assertTrue(request.called)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(respx.stats.call_count, 0)
            self.assertEqual(httpx_mock.stats.call_count, 1)

        self.assertEqual(httpx_mock.stats.call_count, 0)

    async def test_async_local_contextmanager(self):
        async with respx.mock() as httpx_mock:
            self.assertEqual(respx.stats.call_count, 0)
            self.assertEqual(httpx_mock.stats.call_count, 0)

            request = httpx_mock.get("https://foo/bar/", status_code=202)
            response = await httpx.get("https://foo/bar/")

            self.assertTrue(request.called)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(respx.stats.call_count, 0)
            self.assertEqual(httpx_mock.stats.call_count, 1)

        self.assertEqual(httpx_mock.stats.call_count, 0)

    @respx.mock(assert_all_called=False, assert_all_mocked=False)
    async def test_decorator_with_settings(self, httpx_mock):
        request = httpx_mock.get("https://ham/spam/", status_code=202)
        response = await httpx.get("https://foo/bar/")

        self.assertFalse(request.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(httpx_mock.stats.call_count, 1)

    async def test_start_stop(self):
        url = "https://foo/bar/"
        request = respx.request("GET", url, status_code=202)

        self.assertEqual(respx.stats.call_count, 0)

        try:
            respx.start()
            response = await httpx.get(url)

            self.assertTrue(request.called)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.text, "")
            self.assertEqual(respx.stats.call_count, 1)

            respx.stop(reset=False)
            self.assertEqual(respx.stats.call_count, 1)

            respx.stop()
            self.assertEqual(respx.stats.call_count, 0)

        except Exception:  # pragma: nocover
            # Cleanup global state on error, to not affect other tests
            respx.stop()
            raise

    async def test_http_methods(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            m = httpx_mock.get(url, status_code=404)
            httpx_mock.post(url, status_code=201)
            httpx_mock.put(url, status_code=202)
            httpx_mock.patch(url, status_code=500)
            httpx_mock.delete(url, status_code=204)
            httpx_mock.head(url, status_code=405)
            httpx_mock.options(url, status_code=501)

            response = await httpx.get(url)
            self.assertEqual(response.status_code, 404)
            response = await httpx.post(url)
            self.assertEqual(response.status_code, 201)
            response = await httpx.put(url)
            self.assertEqual(response.status_code, 202)
            response = await httpx.patch(url)
            self.assertEqual(response.status_code, 500)
            response = await httpx.delete(url)
            self.assertEqual(response.status_code, 204)
            response = await httpx.head(url)
            self.assertEqual(response.status_code, 405)
            response = await httpx.options(url)
            self.assertEqual(response.status_code, 501)

            self.assertTrue(m.called)
            self.assertEqual(httpx_mock.stats.call_count, 7)

    async def test_string_url_pattern(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    async def test_regex_url_pattern(self):
        async with respx.HTTPXMock() as httpx_mock:
            url_pattern = re.compile("^https://foo/.*$")
            foobar = httpx_mock.get(url_pattern, content="whatever")
            response = await httpx.get("https://foo/bar/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "whatever")

    async def test_invalid_url_pattern(self):
        async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
            foobar = httpx_mock.get(["invalid"], content="whatever")
            with self.assertRaises(ValueError):
                await httpx.get("https://foo/bar/")

        self.assertFalse(foobar.called)

    async def test_unknown_url(self):
        async with respx.HTTPXMock(
            assert_all_called=False, assert_all_mocked=False
        ) as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.post(url)  # Non-matching method
            response = await httpx.get(url)

            self.assertFalse(foobar.called)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers, httpx.Headers({"Content-Type": "text/plain"})
            )
            self.assertEqual(response.text, "")

            self.assertEqual(httpx_mock.stats.call_count, 1)
            request, response = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNotNone(response)

    async def test_repeated_pattern(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/baz/"
            one = httpx_mock.post(url, status_code=201)
            two = httpx_mock.post(url, status_code=409)
            response1 = await httpx.post(url, json={})
            response2 = await httpx.post(url, json={})
            response3 = await httpx.post(url, json={})

            self.assertEqual(response1.status_code, 201)
            self.assertEqual(response2.status_code, 409)
            self.assertEqual(response3.status_code, 409)
            self.assertEqual(httpx_mock.stats.call_count, 3)

            self.assertTrue(one.called)
            self.assertTrue(one.call_count, 1)
            statuses = [response.status_code for _, response in one.calls]
            self.assertListEqual(statuses, [201])

            self.assertTrue(two.called)
            self.assertTrue(two.call_count, 2)
            statuses = [response.status_code for _, response in two.calls]
            self.assertListEqual(statuses, [409, 409])

    async def test_status_code(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, status_code=404)
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 404)

    async def test_content_type(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content_type="foo/bar")
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers({"Content-Type": "foo/bar"}))

    async def test_headers(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            foobar = httpx_mock.get(url, headers=headers)
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))

        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "foo/bar", "X-Foo": "bar; baz"}
            content_type = "ham/spam"
            foobar = httpx_mock.get(url, content_type=content_type, headers=headers)
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        merged_headers = httpx.Headers(headers)
        merged_headers["Content-Type"] = content_type
        self.assertEqual(response.headers, merged_headers)

    async def test_raw_content(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.post(url, content=b"raw content")
            response = await httpx.post(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.text, "raw content")

    async def test_json_content(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json"}
            content = {"foo": "bar"}
            foobar = httpx_mock.get(url, content=content)  # Headers not passed
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertDictEqual(response.json(), content)

        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            content = ["foo", "bar"]
            foobar = httpx_mock.get(url, headers=headers, content=content)
            response = await httpx.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.headers, httpx.Headers(headers))
        self.assertListEqual(response.json(), content)

    async def test_raising_content(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content=httpx.ConnectTimeout())
            with self.assertRaises(httpx.ConnectTimeout):
                await httpx.get(url)

        self.assertTrue(foobar.called)
        request, response = foobar.calls[-1]
        self.assertIsNotNone(request)
        self.assertIsNone(response)

    async def test_callable_content(self):
        async with respx.HTTPXMock() as httpx_mock:
            url_pattern = re.compile(r"https://foo/bar/(?P<id>\d+)/")
            content = lambda request, id: f"foobar #{id}"
            foobar = httpx_mock.get(url_pattern, content=content)
            response = await httpx.get("https://foo/bar/123/")

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar #123")

    # def test_sync_client(self):
    # with respx.HTTPXMock() as httpx_mock:
    # url = "https://foo/bar/"
    # foobar = httpx_mock.get(url, content="foobar")
    # with httpx.Client() as client:
    # response = client.get(url)

    # self.assertTrue(foobar.called)
    # self.assertEqual(response.status_code, 200)
    # self.assertEqual(response.text, "foobar")

    # async def test_async_client(self):
    # async with respx.HTTPXMock() as httpx_mock:
    # url = "https://foo/bar/"
    # foobar = httpx_mock.get(url, content="foobar")
    # async with httpx.AsyncClient() as client:
    # response = await client.get(url)

    # self.assertTrue(foobar.called)
    # self.assertEqual(response.status_code, 200)
    # self.assertEqual(response.text, "foobar")

    async def test_uds(self):
        async with respx.HTTPXMock() as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, content="foobar")
            async with httpx.Client(uds="/var/run/foobar.sock") as client:
                response = await client.get(url)

        self.assertTrue(foobar.called)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "foobar")

    async def test_alias(self):
        async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
            url = "https://foo/bar/"
            foobar = httpx_mock.get(url, alias="foobar")
            self.assertNotIn("foobar", respx.aliases)
            self.assertIn("foobar", httpx_mock.aliases)
            self.assertEqual(httpx_mock.aliases["foobar"].url, foobar.url)
            self.assertEqual(httpx_mock["foobar"].url, foobar.url)

    async def test_exception(self):
        async with respx.HTTPXMock() as httpx_mock:
            with asynctest.mock.patch(
                "httpx.client.Client._dispatcher_for_request",
                side_effect=ValueError("mock"),
            ):
                url = "https://foo/bar/1/"
                httpx_mock.get(url)
                with self.assertRaises(ValueError):
                    await httpx.get(url)

            self.assertEqual(httpx_mock.stats.call_count, 1)
            request, response = httpx_mock.calls[-1]
            self.assertIsNotNone(request)
            self.assertIsNone(response)

    async def test_custom_matcher(self):
        def matcher(request, response):
            if request.url.host == "foo":
                response.headers["X-Foo"] = "Bar"
                response.content = lambda request, id: f"foobar #{id}"
                response.context["id"] = 123
                return response

        async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
            request = httpx_mock.request(
                matcher, status_code=202, headers={"X-Ham": "Spam"}
            )
            response = await httpx.get("https://foo/bar/")

            self.assertEqual(response.status_code, 202)
            self.assertEqual(
                response.headers,
                httpx.Headers(
                    {"Content-Type": "text/plain", "X-Ham": "Spam", "X-Foo": "Bar"}
                ),
            )
            self.assertEqual(response.text, "foobar #123")
            self.assertTrue(request.called)
            self.assertFalse(request.pass_through)

            with self.assertRaises(ValueError):
                httpx_mock.request(lambda req, res: "invalid")
                await httpx.get("https://ham/spam/")

    async def test_assert_all_called_fail(self):
        with self.assertRaises(AssertionError):
            async with respx.HTTPXMock() as httpx_mock:
                request1 = httpx_mock.get("https://foo/bar/1/", status_code=404)
                request2 = httpx_mock.post("https://foo/bar/", status_code=201)

                response = await httpx.get("https://foo/bar/1/")

                self.assertEqual(response.status_code, 404)
                self.assertTrue(request1.called)
                self.assertFalse(request2.called)

    async def test_assert_all_called_disabled(self):
        async with respx.HTTPXMock(assert_all_called=False) as httpx_mock:
            request1 = httpx_mock.get("https://foo/bar/1/", status_code=404)
            request2 = httpx_mock.post("https://foo/bar/", status_code=201)

            response = await httpx.get("https://foo/bar/1/")

            self.assertEqual(response.status_code, 404)
            self.assertTrue(request1.called)
            self.assertFalse(request2.called)

    async def test_assert_all_called_sucess(self):
        async with respx.HTTPXMock(assert_all_called=True) as httpx_mock:
            request1 = httpx_mock.get("https://foo/bar/1/", status_code=404)
            request2 = httpx_mock.post("https://foo/bar/", status_code=201)

            response = await httpx.get("https://foo/bar/1/")
            response = await httpx.post("https://foo/bar/")

            self.assertEqual(response.status_code, 201)
            self.assertTrue(request1.called)
            self.assertTrue(request2.called)

    async def test_assert_all_mocked_fail(self):
        with self.assertRaises(AssertionError):
            async with respx.HTTPXMock(assert_all_mocked=True) as httpx_mock:
                await httpx.get("https://foo/bar/")

        self.assertEqual(httpx_mock.stats.call_count, 0)

    async def test_assert_all_mocked_disabled(self):
        async with respx.HTTPXMock(assert_all_mocked=False) as httpx_mock:
            response = await httpx.get("https://foo/bar/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(httpx_mock.calls), 1)

    async def test_pass_through_with_arg(self):
        async with respx.HTTPXMock() as httpx_mock:
            request = httpx_mock.get("https://www.example.org/", pass_through=True)

            with asynctest.mock.patch(
                "asyncio.open_connection",
                side_effect=ConnectionRefusedError("test request blocked"),
            ) as open_connection:
                with self.assertRaises(ConnectionRefusedError):
                    await httpx.get("https://www.example.org/")

            self.assertTrue(open_connection.called)
            self.assertTrue(request.called)
            self.assertTrue(request.pass_through)

    async def test_pass_through_with_custom_matcher(self):
        async with respx.HTTPXMock() as httpx_mock:
            request = httpx_mock.request(lambda request, response: request)

            with asynctest.mock.patch(
                "asyncio.open_connection",
                side_effect=ConnectionRefusedError("test request blocked"),
            ) as open_connection:
                with self.assertRaises(ConnectionRefusedError):
                    await httpx.get("https://www.example.org/")

            self.assertTrue(open_connection.called)
            self.assertTrue(request.called)
            self.assertIsNone(request.pass_through)

    @respx.mock
    async def test_stats(self, backend=None):
        url = "https://foo/bar/1/"
        respx.get(re.compile("http://some/url"))
        respx.delete("http://some/url")

        foobar1 = respx.get(url, status_code=202, alias="get_foobar")
        foobar2 = respx.delete(url, status_code=200, alias="del_foobar")

        self.assertFalse(foobar1.called)
        self.assertEqual(foobar1.call_count, len(foobar1.calls))
        self.assertEqual(foobar1.call_count, 0)
        self.assertEqual(respx.stats.call_count, len(respx.calls))
        self.assertEqual(respx.stats.call_count, 0)

        async with httpx.Client(backend=backend) as client:
            get_response = await client.get(url)
            del_response = await client.delete(url)

        self.assertTrue(foobar1.called)
        self.assertTrue(foobar2.called)
        self.assertEqual(foobar1.call_count, 1)
        self.assertEqual(foobar2.call_count, 1)

        _request, _response = foobar1.calls[-1]
        self.assertIsInstance(_request, httpx.Request)
        self.assertIsInstance(_response, httpx.Response)
        self.assertEqual(_request.method, "GET")
        self.assertEqual(_request.url, url)
        self.assertEqual(_response.status_code, 202)
        self.assertEqual(_response.status_code, get_response.status_code)
        self.assertEqual(_response.content, get_response.content)
        self.assertEqual(id(_response), id(get_response))

        _request, _response = foobar2.calls[-1]
        self.assertIsInstance(_request, httpx.Request)
        self.assertIsInstance(_response, httpx.Response)
        self.assertEqual(_request.method, "DELETE")
        self.assertEqual(_request.url, url)
        self.assertEqual(_response.status_code, 200)
        self.assertEqual(_response.status_code, del_response.status_code)
        self.assertEqual(_response.content, del_response.content)
        self.assertEqual(id(_response), id(del_response))

        self.assertEqual(respx.stats.call_count, 2)
        self.assertEqual(respx.calls[0], foobar1.calls[-1])
        self.assertEqual(respx.calls[1], foobar2.calls[-1])

        alias = respx.aliases["get_foobar"]
        self.assertEqual(alias, foobar1)
        self.assertEqual(alias.alias, foobar1.alias)

        alias = respx.aliases["del_foobar"]
        self.assertEqual(alias, foobar2)
        self.assertEqual(alias.alias, foobar2.alias)

    # async def test_sync_stats(self, backend=None):
    # with respx.HTTPXMock() as httpx_mock:
    # url = "https://foo/bar/1/"
    # foobar1 = httpx_mock.get(url, status_code=202, alias="get_foobar")
    # foobar2 = httpx_mock.delete(url, status_code=200, alias="del_foobar")

    # with httpx.Client(backend=backend) as client:
    # get_response = client.get(url)
    # del_response = client.delete(url)

    # self.assertTrue(foobar1.called)
    # self.assertTrue(foobar2.called)
    # self.assertEqual(len(foobar1.calls), 1)
    # self.assertEqual(len(foobar2.calls), 1)
    # self.assertEqual(len(respx.calls), 0)
    # self.assertEqual(len(httpx_mock.calls), 2)
    # self.assertEqual(httpx_mock.calls[0], foobar1.calls[-1])
    # self.assertEqual(httpx_mock.calls[1], foobar2.calls[-1])

    # _request, _response = foobar1.calls[-1]
    # self.assertIsInstance(_request, httpx.AsyncRequest)
    # self.assertIsInstance(_response, httpx.Response)
    # self.assertEqual(_response.content, get_response.content)
    # self.assertEqual(id(_response), id(get_response))
    # self.assertEqual(id(_response.request), id(_request))

    # _request, _response = foobar2.calls[-1]
    # self.assertIsInstance(_request, httpx.AsyncRequest)
    # self.assertIsInstance(_response, httpx.Response)
    # self.assertEqual(_response.content, del_response.content)
    # self.assertEqual(id(_response), id(del_response))
    # self.assertEqual(id(_response.request), id(_request))

    def test_trio_backend(self):
        trio.run(self.test_stats, TrioBackend())

    @respx.mock
    async def test_parallel_requests(self):
        async def content(request, page):
            await asyncio.sleep(0.2 if page == "one" else 0.1)
            return page

        url_pattern = re.compile(r"https://foo/(?P<page>\w+)/$")
        respx.get(url_pattern, content=content)

        responses = await asyncio.gather(
            httpx.get("https://foo/one/"), httpx.get("https://foo/two/")
        )
        response_one, response_two = responses

        self.assertEqual(response_one.text, "one")
        self.assertEqual(response_two.text, "two")

        self.assertEqual(respx.stats.call_count, 2)