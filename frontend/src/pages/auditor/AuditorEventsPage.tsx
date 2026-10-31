import React, { useState, useEffect, useMemo } from 'react';
import { 
  Search, ShieldCheck, Copy, Check, ChevronRight, FileText, X
} from 'lucide-react';
import { mockService } from '../../services/mock/mockService';
import { AuditEvent } from '../../contracts/models';
import { UserRole } from '../../contracts/enums';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Button,
  LoadingSpinner,
} from '../../components/ui';

export const AuditorEventsPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [resourceFilter, setResourceFilter] = useState<string>('ALL');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvents = async () => {
      setLoading(true);
      try {
        const data = await mockService.listAuditEvents();
        setEvents(data);
      } catch (err) {
        console.error('Failed to load audit events:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, []);

  const copyToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      const matchesSearch = 
        e.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.event_hash.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.resource_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (e.actor_role && e.actor_role.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesResource = resourceFilter === 'ALL' || e.resource_type === resourceFilter;
      const matchesRole = roleFilter === 'ALL' || e.actor_role === roleFilter;

      return matchesSearch && matchesResource && matchesRole;
    });
  }, [events, searchQuery, resourceFilter, roleFilter]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <LoadingSpinner size="lg" label="Loading cryptographic ledger..." />
      </div>
    );
  }

  const resourceTypes = Array.from(new Set(events.map(e => e.resource_type))).filter(Boolean);

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* ── Page Header ───────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 md:p-8 rounded-card border border-subtle shadow-card">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-pill bg-elevated text-muted border border-subtle">
              IMMUTABLE AUDIT LOG
            </span>
            <span className="text-xs text-muted font-mono font-medium">
              Total {events.length} Sealed Records
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-ink tracking-tight">Tamper-Evident Event Ledger</h1>
          <p className="text-xs text-muted mt-1 font-medium">
            Deterministic cryptographic audit trail of candidate actions, OCR extractions, and reviewer determinations.
          </p>
        </div>
      </div>

      {/* ── Filter and Search Bar ──────────────────────────────── */}
      <div className="bg-surface p-4 rounded-card border border-subtle shadow-card flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Hash, Action, Resource ID, or Actor Role..."
            className="w-full pl-11 pr-4 py-2 bg-elevated border border-subtle rounded-pill text-xs text-ink placeholder:text-muted focus:outline-none focus:border-subtle-strong font-medium"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto">
          <select
            value={resourceFilter}
            onChange={(e) => setResourceFilter(e.target.value)}
            className="text-xs font-semibold bg-elevated border border-subtle rounded-pill px-3.5 py-2 text-ink focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-surface text-ink">All Resource Types</option>
            {resourceTypes.map(t => (
              <option key={t} value={t} className="bg-surface text-ink">{t}</option>
            ))}
          </select>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="text-xs font-semibold bg-elevated border border-subtle rounded-pill px-3.5 py-2 text-ink focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-surface text-ink">All Actor Roles</option>
            {Object.values(UserRole).map(r => (
              <option key={r} value={r} className="bg-surface text-ink">{r}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Ledger Table Card ─────────────────────────────────── */}
      <div className="bg-surface rounded-card p-6 border border-subtle shadow-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Seq #</TableHead>
              <TableHead>Timestamp</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Actor Role</TableHead>
              <TableHead>SHA-256 Event Hash</TableHead>
              <TableHead className="text-right">Inspect</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-muted font-medium">
                  No audit records match the selected query.
                </TableCell>
              </TableRow>
            ) : (
              filteredEvents.map(event => (
                <TableRow 
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  className="cursor-pointer group"
                >
                  <TableCell className="font-mono font-semibold text-accent">
                    #{event.sequence_number}
                  </TableCell>
                  <TableCell className="text-muted font-medium whitespace-nowrap text-xs">
                    {new Date(event.timestamp).toLocaleString([], { 
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' 
                    })}
                  </TableCell>
                  <TableCell>
                    <span className="font-medium text-ink inline-block px-2.5 py-1 rounded-pill bg-elevated text-[11px] border border-subtle">
                      {event.action}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-ink">
                    {event.resource_type} <span className="text-muted text-[11px]">({event.resource_id.slice(0, 8)})</span>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium text-muted capitalize text-xs">{event.actor_role || 'SYSTEM'}</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5 font-mono text-[11px] text-accent bg-accent-dim border border-accent/30 px-2.5 py-0.5 rounded-pill w-fit font-medium">
                      <span>{event.event_hash.slice(0, 16)}...</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(event.event_hash);
                        }}
                        className="text-muted hover:text-ink p-0.5 cursor-pointer"
                        title="Copy full hash"
                      >
                        {copiedHash === event.event_hash ? (
                          <Check className="w-3 h-3 text-accent" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <ChevronRight className="w-4 h-4 text-muted group-hover:text-accent transition-colors inline-block" />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── State Delta Inspection Drawer ─────────────────────── */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/80">
          <div 
            className="w-full max-w-xl h-full bg-surface border-l border-subtle shadow-modal p-6 md:p-8 overflow-y-auto flex flex-col justify-between"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-6">
              {/* Drawer Header */}
              <div className="flex items-center justify-between pb-4 border-b border-subtle">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-sm bg-elevated border border-subtle text-accent font-mono text-xs font-semibold flex items-center justify-center">
                    #{selectedEvent.sequence_number}
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-ink">{selectedEvent.action}</h3>
                    <p className="text-xs text-muted font-mono">ID: {selectedEvent.id}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="p-2 rounded-sm text-muted hover:text-ink hover:bg-elevated transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Cryptographic Linkage Info */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-accent" /> Hash Signatures
                </h4>
                
                <div className="space-y-2">
                  <div>
                    <span className="text-muted text-xs block mb-1 font-medium">Previous Block Hash (Parent):</span>
                    <code className="text-xs font-mono text-ink bg-elevated p-2.5 rounded-sm block break-all border border-subtle">
                      {selectedEvent.previous_hash || '0000000000000000000000000000000000000000000000000000000000000000'}
                    </code>
                  </div>
                  <div>
                    <span className="text-muted text-xs block mb-1 font-medium">Current Block Hash (SHA-256):</span>
                    <code className="text-xs font-mono text-accent bg-accent-dim p-2.5 rounded-sm block break-all border border-accent/30 font-medium">
                      {selectedEvent.event_hash}
                    </code>
                  </div>
                </div>
              </div>

              {/* Actor & Entity Info */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-sm bg-elevated border border-subtle font-medium">
                  <span className="text-muted block mb-1">Actor Identity</span>
                  <p className="font-semibold text-ink capitalize">{selectedEvent.actor_role || 'System'}</p>
                  <p className="text-[11px] text-muted font-mono">{selectedEvent.actor_id || 'automated-pipeline'}</p>
                </div>
                <div className="p-3.5 rounded-sm bg-elevated border border-subtle font-medium">
                  <span className="text-muted block mb-1">Target Resource</span>
                  <p className="font-semibold text-ink">{selectedEvent.resource_type}</p>
                  <p className="text-[11px] text-muted font-mono">{selectedEvent.resource_id}</p>
                </div>
              </div>

              {/* State Delta Payload */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-accent" /> Payload State Delta
                </h4>
                <div className="bg-elevated text-ink p-4 rounded-sm text-xs font-mono overflow-x-auto border border-subtle">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(eventDetailsPayload(selectedEvent), null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Close Button */}
            <div className="pt-6 border-t border-subtle">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setSelectedEvent(null)}
                className="w-full justify-center"
              >
                Close Inspector
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const eventDetailsPayload = (event: AuditEvent) => {
  return event.details || event.new_state || { status: 'RECORD_SEALED', timestamp: event.timestamp };
};
