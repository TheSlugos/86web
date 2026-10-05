import test, { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { sanitizeConfig, parseAndValidateVMConfig, exportVMConfig } from '../vmConfig.ts'
import type { VMConfig } from '../../types/index.ts'

describe('VM Configuration Utilities', () => {
  describe('sanitizeConfig', () => {
    it('strips private VM media paths while preserving shared library paths', () => {
      const input = {
        machine: 'ibm_at',
        cpu_family: 'i286',
        cpu_speed: 12,
        mem_size: 4096,
        fdd_01_fn: '/data/vms/123-uuid/media/boot.img',
        fdd_02_fn: '/library/dos622/disk1.img',
        fdd_03_fn: 'custom/vms/test.img',
        fdd_04_fn: '',
        cdrom_01_fn: '/data/vms/456-uuid/media/win95.iso',
        cdrom_02_fn: '/library/iso/office.iso',
      } as unknown as VMConfig

      const result = sanitizeConfig(input)

      // Strips paths containing /vms/
      assert.strictEqual(result.fdd_01_fn, '')
      assert.strictEqual(result.fdd_03_fn, '')
      assert.strictEqual(result.cdrom_01_fn, '')

      // Preserves /library/ and empty paths
      assert.strictEqual(result.fdd_02_fn, '/library/dos622/disk1.img')
      assert.strictEqual(result.cdrom_02_fn, '/library/iso/office.iso')
      assert.strictEqual(result.fdd_04_fn, '')

      // Preserves general machine config
      assert.strictEqual(result.machine, 'ibm_at')
      assert.strictEqual(result.cpu_family, 'i286')
      assert.strictEqual((result as any).mem_size, 4096)
    })

    it('returns a shallow copy and does not mutate the original object', () => {
      const input = {
        machine: 'super7',
        fdd_01_fn: '/data/vms/foo/media/dos.img',
      } as unknown as VMConfig

      const result = sanitizeConfig(input)
      assert.strictEqual(result.fdd_01_fn, '')
      assert.strictEqual(input.fdd_01_fn, '/data/vms/foo/media/dos.img')
    })
  })

  describe('parseAndValidateVMConfig', () => {
    const validConfigPayload = {
      format: '86web-vm-config',
      version: 1,
      name: 'Retro 486 DX2',
      description: 'DOS 6.22 and Windows 3.11 setup',
      config: {
        machine: 'award486',
        cpu_family: 'i486dx2',
        cpu: '66',
        memory: 16,
        fdd_01_fn: '/data/vms/999/media/boot.img',
        cdrom_01_fn: '/library/cdroms/win311.iso',
      },
    }

    it('parses valid configuration and sanitizes private media paths', () => {
      const jsonText = JSON.stringify(validConfigPayload)
      const parsed = parseAndValidateVMConfig(jsonText, [])

      assert.strictEqual(parsed.name, 'Retro 486 DX2')
      assert.strictEqual(parsed.description, 'DOS 6.22 and Windows 3.11 setup')
      assert.strictEqual(parsed.config.machine, 'award486')
      assert.strictEqual(parsed.config.fdd_01_fn, '') // sanitized
      assert.strictEqual(parsed.config.cdrom_01_fn, '/library/cdroms/win311.iso') // kept
    })

    it('rejects malformed JSON', () => {
      assert.throws(
        () => parseAndValidateVMConfig('NOT_VALID_JSON{', []),
        /Invalid JSON file/
      )
    })

    it('rejects JSON that is not an object', () => {
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(['array', 'value']), []),
        /Config file must be a JSON object/
      )
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify('just a string'), []),
        /Config file must be a JSON object/
      )
    })

    it('rejects unsupported format tags', () => {
      const payload = { ...validConfigPayload, format: 'unknown-format-tag' }
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(payload), []),
        /Unsupported config format "unknown-format-tag"/
      )
    })

    it('rejects missing or empty VM name', () => {
      const payloadNoName = { ...validConfigPayload, name: '' }
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(payloadNoName), []),
        /missing or invalid VM name/
      )

      const payloadNullName = { ...validConfigPayload, name: null }
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(payloadNullName), []),
        /missing or invalid VM name/
      )
    })

    it('rejects missing hardware configuration object', () => {
      const payloadNoConfig = { ...validConfigPayload, config: null }
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(payloadNoConfig), []),
        /missing hardware configuration object/
      )
    })

    it('rejects configuration missing machine identifier', () => {
      const payloadNoMachine = {
        ...validConfigPayload,
        config: { cpu_family: 'i486' },
      }
      assert.throws(
        () => parseAndValidateVMConfig(JSON.stringify(payloadNoMachine), []),
        /missing machine identifier in configuration/
      )
    })

    it('deduplicates names on collision with incrementing counters', () => {
      const jsonText = JSON.stringify(validConfigPayload)

      // Collision 1: 'Retro 486 DX2' exists -> 'Retro 486 DX2 (Imported)'
      const res1 = parseAndValidateVMConfig(jsonText, ['Retro 486 DX2'])
      assert.strictEqual(res1.name, 'Retro 486 DX2 (Imported)')

      // Collision 2: both original and '(Imported)' exist -> 'Retro 486 DX2 (Imported 2)'
      const res2 = parseAndValidateVMConfig(jsonText, [
        'Retro 486 DX2',
        'Retro 486 DX2 (Imported)',
      ])
      assert.strictEqual(res2.name, 'Retro 486 DX2 (Imported 2)')

      // Collision 3: multiple exist -> 'Retro 486 DX2 (Imported 3)'
      const res3 = parseAndValidateVMConfig(jsonText, [
        'Retro 486 DX2',
        'Retro 486 DX2 (Imported)',
        'Retro 486 DX2 (Imported 2)',
      ])
      assert.strictEqual(res3.name, 'Retro 486 DX2 (Imported 3)')
    })
  })

  describe('exportVMConfig', () => {
    it('generates expected structure and sanitized filename', () => {
      let createdBlob: Blob | null = null
      let downloadFilename = ''
      let clicked = false
      let revokedUrl = ''

      // Mock DOM environment for Node
      const originalDocument = globalThis.document
      const originalURL = globalThis.URL

      globalThis.document = {
        createElement: (tag: string) => {
          if (tag === 'a') {
            return {
              href: '',
              download: '',
              click: () => {
                clicked = true
              },
            } as any
          }
          return {} as any
        },
      } as any

      globalThis.URL.createObjectURL = (blob: any) => {
        createdBlob = blob
        return 'blob:mock-url'
      }
      globalThis.URL.revokeObjectURL = (url: string) => {
        revokedUrl = url
      }

      try {
        const vm = {
          name: 'Windows 98 Second Edition!',
          description: 'Gaming Rig',
          config: {
            machine: 'super7',
            fdd_01_fn: '/data/vms/id1/media/boot98.img',
            cdrom_01_fn: '/library/win98se.iso',
          } as unknown as VMConfig,
        }

        exportVMConfig(vm as any)

        assert.strictEqual(clicked, true)
        assert.strictEqual(revokedUrl, 'blob:mock-url')
        assert.ok(createdBlob)
      } finally {
        globalThis.document = originalDocument
        globalThis.URL = originalURL
      }
    })
  })
})
