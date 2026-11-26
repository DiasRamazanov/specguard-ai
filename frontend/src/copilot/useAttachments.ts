// Copilot attachments for one audit: upload, extraction status, removal and retry.
import { useCallback, useRef, useState } from 'react'
import { ApiError, type SpecGuardClient } from '../api/client'
import type { Attachment, AttachmentPurpose } from '../api/types'
import { validateFile } from '../state/useAudit'

export type ChipState = 'uploading' | 'extracted' | 'error' | 'removing'

export interface AttachmentChip {
  localId: string
  file: File
  purpose: AttachmentPurpose
  state: ChipState
  attachment?: Attachment
  error?: string
  /** Included in the next Copilot request / comparison. */
  selected: boolean
}

let n = 0
const id = () => `att-${Date.now().toString(36)}-${(n++).toString(36)}`

export function useAttachments(client: SpecGuardClient, auditId: string | null, hooks: { onChange: (ok: boolean) => void; onError: (m: string) => void }) {
  const [chips, setChips] = useState<AttachmentChip[]>([])
  const ref = useRef<AttachmentChip[]>([])
  const hooksRef = useRef(hooks)
  hooksRef.current = hooks

  const commit = useCallback((next: AttachmentChip[]) => {
    ref.current = next
    setChips(next)
  }, [])
  const patch = useCallback(
    (localId: string, p: Partial<AttachmentChip>) => commit(ref.current.map((c) => (c.localId === localId ? { ...c, ...p } : c))),
    [commit],
  )

  const upload = useCallback(
    async (chip: AttachmentChip) => {
      if (!auditId) return
      let ok = false
      try {
        const attachment = await client.addAttachment(auditId, chip.file, chip.file.name, chip.purpose)
        patch(chip.localId, { state: 'extracted', attachment, error: undefined })
        ok = true
      } catch (err) {
        const message = err instanceof ApiError ? err.detail : 'Не удалось прикрепить файл.'
        patch(chip.localId, { state: 'error', error: message })
        hooksRef.current.onError(message)
      } finally {
        hooksRef.current.onChange(ok)
      }
    },
    [auditId, client, patch],
  )

  const add = useCallback(
    (files: FileList | File[], purpose: AttachmentPurpose) => {
      const next = [...ref.current]
      const started: AttachmentChip[] = []
      for (const file of Array.from(files)) {
        if (next.some((c) => c.file.name === file.name && c.file.size === file.size && c.purpose === purpose)) continue
        const problem = validateFile(file)
        const chip: AttachmentChip = { localId: id(), file, purpose, state: problem ? 'error' : 'uploading', error: problem ?? undefined, selected: true }
        next.push(chip)
        if (!problem) started.push(chip)
      }
      commit(next)
      started.forEach((c) => void upload(c))
    },
    [commit, upload],
  )

  const remove = useCallback(
    async (localId: string) => {
      const chip = ref.current.find((c) => c.localId === localId)
      if (!chip) return
      if (chip.attachment && auditId) {
        patch(localId, { state: 'removing' })
        try {
          await client.removeAttachment(auditId, chip.attachment.attachment_id)
        } catch (err) {
          // 404 means the server already forgot it (e.g. session expiry); the chip can go.
          if (!(err instanceof ApiError && err.status === 404)) {
            const message = err instanceof ApiError ? err.detail : 'Не удалось удалить вложение.'
            patch(localId, { state: 'extracted', error: message })
            hooksRef.current.onError(message)
            return
          }
        }
      }
      commit(ref.current.filter((c) => c.localId !== localId))
    },
    [auditId, client, commit, patch],
  )

  const retry = useCallback(
    (localId: string) => {
      const chip = ref.current.find((c) => c.localId === localId)
      if (!chip || validateFile(chip.file)) return
      patch(localId, { state: 'uploading', error: undefined })
      void upload(chip)
    },
    [patch, upload],
  )

  const toggle = useCallback((localId: string) => {
    const chip = ref.current.find((c) => c.localId === localId)
    if (chip) patch(localId, { selected: !chip.selected })
  }, [patch])

  return { chips, add, remove, retry, toggle }
}
