import { ApiError, SpecGuardClient, contentTypeFor, isAcceptedFile } from '../api/client'

function mockFetch(responses: Array<{ status: number; body?: unknown }>) {
  const calls: Array<{ url: string; init: RequestInit }> = []
  const fn = vi.fn(async (url: string, init: RequestInit = {}) => {
    calls.push({ url, init })
    const r = responses.shift() ?? { status: 200, body: {} }
    return new Response(r.body === undefined ? null : JSON.stringify(r.body), { status: r.status })
  })
  return { fn: fn as unknown as typeof fetch, calls }
}

describe('SpecGuardClient', () => {
  it('creates a session and sends the bearer token on private routes', async () => {
    const { fn, calls } = mockFetch([
      { status: 201, body: { token: 'tok', ttl_seconds: 3600 } },
      { status: 200, body: { audit_id: 'a', status: 'running', events: [] } },
    ])
    const c = new SpecGuardClient(fn)
    await c.createSession()
    await c.auditStatus('a')
    expect(calls[0].url).toBe('/api/sessions')
    expect(new Headers(calls[1].init.headers).get('Authorization')).toBe('Bearer tok')
  })

  it('uploads raw bytes with the filename in the query string', async () => {
    const { fn, calls } = mockFetch([{ status: 201, body: { document_id: 'd' } }])
    await new SpecGuardClient(fn).uploadDocument(new Blob(['# x']), 'ТЗ v2.md')
    expect(calls[0].url).toBe('/api/documents?filename=%D0%A2%D0%97%20v2.md')
    expect(new Headers(calls[0].init.headers).get('Content-Type')).toBe('text/markdown')
    expect(calls[0].init.body).toBeInstanceOf(Blob)
  })

  it('sends attachment purpose and filename', async () => {
    const { fn, calls } = mockFetch([{ status: 201, body: {} }])
    await new SpecGuardClient(fn).addAttachment('a1', new Blob(['x']), 'r.pdf', 'comparison')
    expect(calls[0].url).toBe('/api/audits/a1/attachments?purpose=comparison&filename=r.pdf')
    expect(new Headers(calls[0].init.headers).get('Content-Type')).toBe('application/pdf')
  })

  it('removes an attachment with DELETE', async () => {
    const { fn, calls } = mockFetch([{ status: 204 }])
    await new SpecGuardClient(fn).removeAttachment('a1', 'att1')
    expect(calls[0].url).toBe('/api/audits/a1/attachments/att1')
    expect(calls[0].init.method).toBe('DELETE')
  })

  it('surfaces the backend ErrorResponse detail', async () => {
    const { fn } = mockFetch([{ status: 503, body: { detail: 'Сервер не настроен для внешнего анализа.' } }])
    const err = await new SpecGuardClient(fn).copilot('a', { question: 'q', mode: 'offline', allow_external_processing: false }).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).status).toBe(503)
    expect((err as ApiError).detail).toBe('Сервер не настроен для внешнего анализа.')
  })

  it('creates only one session for concurrent callers', async () => {
    const { fn, calls } = mockFetch([{ status: 201, body: { token: 't', ttl_seconds: 1 } }])
    const c = new SpecGuardClient(fn)
    const created = await Promise.all([c.ensureSession(), c.ensureSession(), c.ensureSession()])
    expect(calls).toHaveLength(1)
    expect(created.filter(Boolean)).toHaveLength(1)
  })

  it('accepts only formats the backend parses', () => {
    expect(isAcceptedFile('a.PDF')).toBe(true)
    expect(isAcceptedFile('a.md')).toBe(true)
    expect(isAcceptedFile('a.txt')).toBe(true)
    expect(isAcceptedFile('a.docx')).toBe(false)
    expect(contentTypeFor('x.markdown')).toBe('text/markdown')
  })
})
