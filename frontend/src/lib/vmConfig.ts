import type { VM, VMConfig } from '../types/index.ts'

/**
 * Sanitizes a VMConfig for export/import to avoid leaking
 * references to other VMs' private media folders.
 */
export function sanitizeConfig(rawConfig: VMConfig): VMConfig {
  const cfg = { ...rawConfig }
  const mediaKeys = [
    'fdd_01_fn', 'fdd_02_fn', 'fdd_03_fn', 'fdd_04_fn',
    'cdrom_01_fn', 'cdrom_02_fn', 'cdrom_03_fn', 'cdrom_04_fn',
  ] as const

  for (const key of mediaKeys) {
    const val = (cfg as any)[key]
    // If the path contains /vms/ (referencing a private VM media dir), clear it.
    // Paths inside /library/ (shared media library) are kept intact.
    if (typeof val === 'string' && val.includes('/vms/')) {
      (cfg as any)[key] = ''
    }
  }
  return cfg
}

export function exportVMConfig(vm: Pick<VM, 'name'> & Partial<Pick<VM, 'description' | 'config'>>) {
  const data = {
    format: '86web-vm-config',
    version: 1,
    exported_at: new Date().toISOString(),
    name: vm.name,
    description: vm.description || '',
    config: vm.config ? sanitizeConfig(vm.config) : {},
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${(vm.name || 'vm').replace(/[^a-z0-9]/gi, '_').toLowerCase()}_config.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function parseAndValidateVMConfig(
  text: string,
  existingNames: string[]
): { name: string; description: string; config: VMConfig } {
  let parsed: any
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('Invalid JSON file')
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Config file must be a JSON object')
  }

  if (parsed.format && parsed.format !== '86web-vm-config') {
    throw new Error(`Unsupported config format "${parsed.format}"`)
  }

  if (!parsed.name || typeof parsed.name !== 'string') {
    throw new Error('Invalid config: missing or invalid VM name')
  }

  if (!parsed.config || typeof parsed.config !== 'object') {
    throw new Error('Invalid config: missing hardware configuration object')
  }

  if (!parsed.config.machine) {
    throw new Error('Invalid config: missing machine identifier in configuration')
  }

  const cleanConfig = sanitizeConfig(parsed.config)

  // Disambiguate name with counter loop if collision exists
  const existingSet = new Set(existingNames)
  let newName = parsed.name
  let counter = 1
  while (existingSet.has(newName)) {
    newName = `${parsed.name} (Imported${counter > 1 ? ` ${counter}` : ''})`
    counter++
  }

  return {
    name: newName,
    description: parsed.description || '',
    config: cleanConfig,
  }
}
