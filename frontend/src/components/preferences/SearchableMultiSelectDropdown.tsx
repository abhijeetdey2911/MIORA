import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from 'react';
import { Check, ChevronDown, Plus, Search, X } from 'lucide-react';

interface SearchableMultiSelectDropdownProps {
  id: string;
  label: string;
  placeholder: string;
  searchPlaceholder: string;
  options: readonly string[];
  selectedValues: string[];
  customActionLabel: string;
  customInputPlaceholder: string;
  error?: string;
  onChange: (nextValues: string[]) => void;
}

export function SearchableMultiSelectDropdown({
  id,
  label,
  placeholder,
  searchPlaceholder,
  options,
  selectedValues,
  customActionLabel,
  customInputPlaceholder,
  error,
  onChange,
}: SearchableMultiSelectDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddingCustom, setIsAddingCustom] = useState(false);
  const [customDraft, setCustomDraft] = useState('');

  const containerRef = useRef<HTMLDivElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const customInputRef = useRef<HTMLInputElement | null>(null);
  const menuPanelRef = useRef<HTMLDivElement | null>(null);

  // Combine predefined options with any already-selected custom/existing values
  // so preserved values when editing are always visible in the list too.
  const combinedOptions = useMemo(() => {
    const seen = new Set<string>();
    const list: string[] = [];
    for (const opt of options) {
      const key = opt.trim().toLowerCase();
      if (key && !seen.has(key)) {
        seen.add(key);
        list.push(opt.trim());
      }
    }
    for (const selected of selectedValues) {
      const key = selected.trim().toLowerCase();
      if (key && !seen.has(key)) {
        seen.add(key);
        list.push(selected.trim());
      }
    }
    return list;
  }, [options, selectedValues]);

  const selectedLowerSet = useMemo(
    () => new Set(selectedValues.map((item) => item.toLowerCase())),
    [selectedValues],
  );

  const filteredOptions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return combinedOptions;
    return combinedOptions.filter((option) => option.toLowerCase().includes(q));
  }, [combinedOptions, searchQuery]);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchQuery('');
        setIsAddingCustom(false);
        setCustomDraft('');
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [isOpen]);

  // Focus search input and ensure dropdown panel is visible inside modal scroll area
  useEffect(() => {
    if (!isOpen) return;
    const frame = window.requestAnimationFrame(() => {
      searchInputRef.current?.focus();
      menuPanelRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [isOpen]);

  useEffect(() => {
    if (!isAddingCustom) return;
    const frame = window.requestAnimationFrame(() => {
      customInputRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [isAddingCustom]);

  const toggleOption = (option: string) => {
    const trimmed = option.trim();
    if (!trimmed) return;
    const lower = trimmed.toLowerCase();

    if (selectedLowerSet.has(lower)) {
      onChange(selectedValues.filter((item) => item.toLowerCase() !== lower));
    } else {
      onChange([...selectedValues, trimmed]);
    }
  };

  const addCustomValue = (rawValue: string) => {
    const parts = rawValue
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length === 0) return;

    const seen = new Set(selectedValues.map((item) => item.toLowerCase()));
    const next = [...selectedValues];

    for (const part of parts) {
      const lower = part.toLowerCase();
      if (!seen.has(lower)) {
        seen.add(lower);
        next.push(part);
      }
    }

    onChange(next);
    setCustomDraft('');
    setSearchQuery('');
    setIsAddingCustom(false);
  };

  const removeValue = (valueToRemove: string) => {
    const lower = valueToRemove.toLowerCase();
    onChange(selectedValues.filter((item) => item.toLowerCase() !== lower));
  };

  const handleContainerKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && isOpen) {
      event.stopPropagation();
      setIsOpen(false);
      setSearchQuery('');
      setIsAddingCustom(false);
      setCustomDraft('');
    }
  };

  const trimmedSearch = searchQuery.trim();
  const canQuickAddFromSearch =
    trimmedSearch.length > 0 &&
    !combinedOptions.some((opt) => opt.toLowerCase() === trimmedSearch.toLowerCase()) &&
    !selectedLowerSet.has(trimmedSearch.toLowerCase());

  return (
    <div ref={containerRef} onKeyDown={handleContainerKeyDown} className="relative">
      <label htmlFor={id} className="block text-xs font-medium text-ink">
        {label} <span className="text-accent">*</span>
      </label>

      {/* Dropdown Trigger Button */}
      <button
        id={id}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => {
          setIsOpen((prev) => !prev);
          if (isOpen) {
            setSearchQuery('');
            setIsAddingCustom(false);
            setCustomDraft('');
          }
        }}
        className={`mt-1.5 flex w-full items-center justify-between gap-2 rounded-xl border bg-surface-2 px-3.5 py-2 text-left text-sm transition-colors focus:outline-none ${
          isOpen
            ? 'border-accent ring-1 ring-accent/30'
            : 'border-line hover:border-subtle/50'
        }`}
      >
        <span
          className={`truncate ${
            selectedValues.length > 0 ? 'font-medium text-ink' : 'text-subtle'
          }`}
        >
          {selectedValues.length > 0
            ? `${selectedValues.length} ${
                selectedValues.length === 1 ? 'selected' : 'selected'
              } (${selectedValues.slice(0, 2).join(', ')}${
                selectedValues.length > 2 ? ` +${selectedValues.length - 2}` : ''
              })`
            : placeholder}
        </span>

        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-accent' : ''
          }`}
          strokeWidth={2}
        />
      </button>

      {/* Dropdown Menu Panel */}
      {isOpen && (
        <div
          ref={menuPanelRef}
          className="mt-1.5 w-full overflow-hidden rounded-xl border border-line bg-surface shadow-card transition-all"
        >
          {/* Search Input inside Dropdown */}
          <div className="flex items-center gap-2 border-b border-line bg-surface-2 px-3 py-2">
            <Search className="h-3.5 w-3.5 shrink-0 text-subtle" strokeWidth={2} />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (canQuickAddFromSearch) {
                    addCustomValue(trimmedSearch);
                  } else if (filteredOptions.length === 1) {
                    toggleOption(filteredOptions[0]);
                  }
                }
              }}
              placeholder={searchPlaceholder}
              aria-label={searchPlaceholder}
              className="min-w-0 flex-1 bg-transparent text-xs text-ink placeholder:text-subtle focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
                className="rounded p-0.5 text-subtle transition-colors hover:text-ink"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Options List */}
          <ul
            role="listbox"
            aria-multiselectable="true"
            aria-label={label}
            className="max-h-48 overflow-y-auto divide-y divide-line/50 p-1.5"
          >
            {filteredOptions.length === 0 ? (
              <li className="px-3 py-2.5 text-xs text-muted">
                No matching options found.
              </li>
            ) : (
              filteredOptions.map((option) => {
                const isSelected = selectedLowerSet.has(option.toLowerCase());
                return (
                  <li key={option} role="option" aria-selected={isSelected}>
                    <button
                      type="button"
                      onClick={() => toggleOption(option)}
                      className={`flex w-full items-center justify-between gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                        isSelected
                          ? 'bg-accent-soft font-semibold text-accent-ink'
                          : 'text-ink hover:bg-surface-2'
                      }`}
                    >
                      <span className="truncate">{option}</span>
                      <span
                        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                          isSelected
                            ? 'border-accent bg-accent text-white'
                            : 'border-line bg-surface-2'
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3" strokeWidth={2.6} />}
                      </span>
                    </button>
                  </li>
                );
              })
            )}
          </ul>

          {/* Add Custom Option Section */}
          <div className="border-t border-line bg-surface-2 p-2">
            {canQuickAddFromSearch && !isAddingCustom && (
              <button
                type="button"
                onClick={() => addCustomValue(trimmedSearch)}
                className="mb-1.5 flex w-full items-center gap-1.5 rounded-lg bg-accent-soft px-2.5 py-1.5 text-left text-xs font-semibold text-accent-ink transition-colors hover:bg-accent hover:text-white"
              >
                <Plus className="h-3.5 w-3.5 shrink-0" strokeWidth={2.3} />
                <span className="truncate">
                  {customActionLabel}: “{trimmedSearch}”
                </span>
              </button>
            )}

            {!isAddingCustom ? (
              <button
                type="button"
                onClick={() => {
                  setIsAddingCustom(true);
                  if (trimmedSearch) {
                    setCustomDraft(trimmedSearch);
                  }
                }}
                className="flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-surface"
              >
                <span className="inline-flex items-center gap-1.5">
                  <Plus className="h-3.5 w-3.5" strokeWidth={2.3} />
                  {customActionLabel}
                </span>
                <span className="text-[10px] text-muted">Custom entry</span>
              </button>
            ) : (
              <div className="flex items-center gap-1.5">
                <input
                  ref={customInputRef}
                  type="text"
                  value={customDraft}
                  onChange={(e) => setCustomDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      if (customDraft.trim()) {
                        addCustomValue(customDraft);
                      }
                    } else if (e.key === 'Escape') {
                      e.stopPropagation();
                      setIsAddingCustom(false);
                      setCustomDraft('');
                    }
                  }}
                  placeholder={customInputPlaceholder}
                  className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (customDraft.trim()) {
                      addCustomValue(customDraft);
                    }
                  }}
                  className="shrink-0 rounded-lg bg-accent px-2.5 py-1.5 text-xs font-semibold text-white transition hover:brightness-105"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsAddingCustom(false);
                    setCustomDraft('');
                  }}
                  aria-label="Cancel custom entry"
                  className="shrink-0 rounded-lg border border-line bg-surface p-1.5 text-muted hover:text-ink"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Selected Items as Removable Tags/Chips */}
      {selectedValues.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {selectedValues.map((value) => (
            <span
              key={value}
              className="inline-flex items-center gap-1.5 rounded-lg border border-accent/25 bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent-ink"
            >
              {value}
              <button
                type="button"
                onClick={() => removeValue(value)}
                aria-label={`Remove ${value}`}
                className="rounded text-accent-ink/75 transition-colors hover:text-rose-500"
              >
                <X className="h-3 w-3" strokeWidth={2.3} />
              </button>
            </span>
          ))}
        </div>
      )}

      {error && <p className="mt-1 text-xs text-rose-500">{error}</p>}
    </div>
  );
}

