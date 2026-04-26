from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _request_json(method: str, url: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        status = resp.status
        raw = resp.read().decode('utf-8')
        if not raw:
            return status, None
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, raw


def _request_sse(url: str, headers: dict[str, str], body: dict[str, Any]) -> tuple[int, str]:
    req = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode('utf-8'),
        method='POST',
        headers=headers,
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        status = resp.status
        collected: list[str] = []

        for raw in resp:
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line.startswith('data:'):
                continue

            data = line[5:].strip()
            if not data or data == '[DONE]':
                continue

            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue

            if isinstance(event, dict):
                # Chat Completions stream
                choices = event.get('choices')
                if isinstance(choices, list) and choices:
                    delta = choices[0].get('delta', {}) if isinstance(choices[0], dict) else {}
                    text = delta.get('content') if isinstance(delta, dict) else None
                    if isinstance(text, str) and text:
                        collected.append(text)

                # Responses API stream
                event_type = event.get('type')
                if event_type == 'response.output_text.delta':
                    delta = event.get('delta')
                    if isinstance(delta, str) and delta:
                        collected.append(delta)

        return status, ''.join(collected).strip()


def _extract_first_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ''

    choices = payload.get('choices')
    if isinstance(choices, list) and choices:
        message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
        content = message.get('content') if isinstance(message, dict) else ''
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get('text')
                    if isinstance(text, str):
                        parts.append(text)
            return ''.join(parts).strip()

    output_text = payload.get('output_text')
    if isinstance(output_text, str):
        return output_text.strip()

    output = payload.get('output')
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get('content')
            if not isinstance(content, list):
                continue
            for sub in content:
                if isinstance(sub, dict):
                    text = sub.get('text')
                    if isinstance(text, str):
                        parts.append(text)
        return ''.join(parts).strip()

    return ''


def _signin(base_url: str, email: str, password: str) -> str:
    status, payload = _request_json(
        method='POST',
        url=f'{base_url}/api/v1/auths/signin',
        headers={'Content-Type': 'application/json'},
        body={'email': email, 'password': password},
    )
    if status < 200 or status >= 300 or not isinstance(payload, dict):
        raise RuntimeError('signin failed')

    token = payload.get('token') or payload.get('access_token')
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError('signin returned no token')
    return token.strip()


def _signin_trusted_header(base_url: str, trusted_header: str, trusted_email: str) -> str:
    status, payload = _request_json(
        method='POST',
        url=f'{base_url}/api/v1/auths/signin',
        headers={trusted_header: trusted_email, 'Content-Type': 'application/json'},
        # SigninForm validation still expects these fields even when trusted header auth is enabled.
        body={'email': 'trusted-header@localhost', 'password': 'unused-password'},
    )
    if status < 200 or status >= 300 or not isinstance(payload, dict):
        raise RuntimeError('trusted-header signin failed')

    token = payload.get('token') or payload.get('access_token')
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError('trusted-header signin returned no token')
    return token.strip()


def _get_auth_headers(base_url: str) -> dict[str, str]:
    bearer = _env('OPENWEBUI_SMOKE_BEARER_TOKEN')
    if bearer:
        return {'Authorization': f'Bearer {bearer}'}

    api_key = _env('OPENWEBUI_SMOKE_API_KEY')
    if api_key:
        return {'Authorization': f'Bearer {api_key}'}

    email = _env('OPENWEBUI_SMOKE_EMAIL')
    password = _env('OPENWEBUI_SMOKE_PASSWORD')
    if email and password:
        token = _signin(base_url, email, password)
        return {'Authorization': f'Bearer {token}'}

    trusted_email = _env('OPENWEBUI_SMOKE_TRUSTED_EMAIL')
    if trusted_email:
        trusted_header = _env('OPENWEBUI_SMOKE_TRUSTED_EMAIL_HEADER', 'Cf-Access-Authenticated-User-Email')
        token = _signin_trusted_header(base_url, trusted_header, trusted_email)
        return {'Authorization': f'Bearer {token}'}

    raise RuntimeError(
        'No auth configured for chat smoke. Set one of: OPENWEBUI_SMOKE_BEARER_TOKEN, '
        'OPENWEBUI_SMOKE_API_KEY, OPENWEBUI_SMOKE_EMAIL+OPENWEBUI_SMOKE_PASSWORD, '
        'OPENWEBUI_SMOKE_TRUSTED_EMAIL.'
    )


def _pick_model(base_url: str, auth_headers: dict[str, str]) -> str:
    model = _env('OPENWEBUI_SMOKE_MODEL')
    if model:
        return model

    status, payload = _request_json(
        method='GET',
        url=f'{base_url}/api/models',
        headers=auth_headers,
    )
    if status < 200 or status >= 300 or not isinstance(payload, dict):
        raise RuntimeError('failed to load model list from /api/models')

    data = payload.get('data')
    if not isinstance(data, list) or not data:
        raise RuntimeError('no models available for smoke test')

    for item in data:
        if isinstance(item, dict):
            model_id = item.get('id')
            if isinstance(model_id, str) and model_id.strip():
                return model_id.strip()

    raise RuntimeError('no usable model id found in /api/models response')


def _resolve_modes() -> list[bool]:
    value = (_env('OPENWEBUI_SMOKE_STREAM') or 'both').lower()

    if value in {'0', 'false', 'no', 'off', 'non-stream', 'nonstream', 'json'}:
        return [False]
    if value in {'1', 'true', 'yes', 'on', 'stream', 'sse'}:
        return [True]
    if value == 'both':
        return [False, True]

    raise RuntimeError(
        'OPENWEBUI_SMOKE_STREAM must be one of: 0, 1, non-stream, stream, both'
    )


def _run_completion(
    base_url: str,
    headers: dict[str, str],
    model: str,
    prompt: str,
    use_stream: bool,
) -> tuple[float, str]:
    payload = {
        'model': model,
        'stream': use_stream,
        'stream_options': {'include_usage': True} if use_stream else None,
        'messages': [{'role': 'user', 'content': prompt}],
        'metadata': {'task': 'chat-smoke'},
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    started = time.time()
    if use_stream:
        status, text = _request_sse(
            url=f'{base_url}/api/chat/completions',
            headers=headers,
            body=payload,
        )
    else:
        status, response_payload = _request_json(
            method='POST',
            url=f'{base_url}/api/chat/completions',
            headers=headers,
            body=payload,
        )
        text = _extract_first_text(response_payload)
    elapsed = time.time() - started

    if status < 200 or status >= 300:
        raise RuntimeError(f'/api/chat/completions returned status {status}')

    if not text:
        mode_label = 'stream' if use_stream else 'non-stream'
        raise RuntimeError(f'chat response is empty for {mode_label} mode')

    return elapsed, text


def main() -> int:
    base_url = _env('OPENWEBUI_SMOKE_BASE_URL', 'http://localhost:3000')
    prompt = _env('OPENWEBUI_SMOKE_PROMPT', 'Please answer with exactly one word: pong')
    modes = _resolve_modes()

    if not base_url:
        raise RuntimeError('OPENWEBUI_SMOKE_BASE_URL is empty')

    auth_headers = _get_auth_headers(base_url)
    model = _pick_model(base_url, auth_headers)

    headers = {'Content-Type': 'application/json', **auth_headers}
    results: list[tuple[bool, float, str]] = []

    for use_stream in modes:
        elapsed, text = _run_completion(base_url, headers, model, prompt, use_stream)
        results.append((use_stream, elapsed, text))

    print('chat-smoke passed')
    print(f'base_url={base_url}')
    print(f'model={model}')
    print('modes=' + ','.join('stream' if use_stream else 'non-stream' for use_stream in modes))
    for use_stream, elapsed, text in results:
        label = 'stream' if use_stream else 'non_stream'
        print(f'{label}_elapsed_sec={elapsed:.2f}')
        print(f'{label}_response_preview={text[:120]}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as error:
        detail = ''
        try:
            detail = error.read().decode('utf-8')
        except Exception:
            detail = str(error)
        print(f'chat-smoke failed: http {error.code} {detail}', file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print(f'chat-smoke failed: {error}', file=sys.stderr)
        raise SystemExit(1)
