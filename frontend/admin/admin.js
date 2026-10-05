/**
 * Techvunex AI Admin Operations Logic
 */
const API_BASE = window.location.origin + '/api/v1';

let allConversations = [];
let allLeads = [];
let allDocuments = [];

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  loadAllData();
});

function setupTabs() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      const tabId = item.getAttribute('data-tab');
      document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
      const target = document.getElementById(`tab-${tabId}`);
      if (target) target.style.display = 'block';

      const titles = {
        overview: 'Operations Overview',
        conversations: 'Visitor Conversations',
        leads: 'Qualified Leads Pipeline',
        kb: 'Knowledge Base Management',
        analytics: 'Analytics & Insights'
      };
      document.getElementById('page-title').innerText = titles[tabId] || 'Dashboard';
    });
  });
}

async function loadAllData() {
  await Promise.all([
    fetchConversations(),
    fetchLeads(),
    fetchKB()
  ]);
  updateKPIs();
}

async function fetchConversations() {
  try {
    const res = await fetch(`${API_BASE}/conversations`);
    if (res.ok) {
      allConversations = await res.json();
      renderConversations();
    }
  } catch (e) {
    console.error('Error fetching conversations:', e);
  }
}

async function fetchLeads() {
  try {
    const res = await fetch(`${API_BASE}/leads`);
    if (res.ok) {
      allLeads = await res.json();
      renderLeads();
    }
  } catch (e) {
    console.error('Error fetching leads:', e);
  }
}

async function fetchKB() {
  try {
    const res = await fetch(`${API_BASE}/kb/documents`);
    if (res.ok) {
      allDocuments = await res.json();
      renderKB();
    }
  } catch (e) {
    console.error('Error fetching KB:', e);
  }
}

function updateKPIs() {
  document.getElementById('kpi-conversations').innerText = allConversations.length;
  document.getElementById('kpi-leads').innerText = allLeads.length;
  
  const qualified = allLeads.filter(l => l.status === 'qualified' || l.status === 'converted').length;
  document.getElementById('kpi-qualified').innerText = qualified;

  const handoffs = allLeads.filter(l => l.human_required || l.status === 'human_required').length;
  document.getElementById('kpi-handoffs').innerText = handoffs;

  // Overview recent table
  const tbody = document.getElementById('overview-convs-body');
  if (tbody) {
    if (!allConversations.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">No conversations yet. Open website demo to start chatting!</td></tr>';
      return;
    }
    tbody.innerHTML = allConversations.slice(0, 5).map(c => `
      <tr>
        <td><code>${c.session_id}</code></td>
        <td><span class="badge badge-new">${c.intent || 'General'}</span></td>
        <td>${c.message_count || 1} msgs</td>
        <td>${new Date(c.updated_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
      </tr>
    `).join('');
  }
}

function renderConversations() {
  const tbody = document.getElementById('convs-table-body');
  if (!tbody) return;

  if (!allConversations.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #94a3b8;">No chat history found.</td></tr>';
    return;
  }

  tbody.innerHTML = allConversations.map(c => `
    <tr>
      <td><strong>${c.title}</strong><br/><small style="color: #64748b;">${c.session_id}</small></td>
      <td><span class="badge badge-new">${c.intent || 'general_question'}</span></td>
      <td>${c.message_count} messages</td>
      <td>${new Date(c.created_at).toLocaleString()}</td>
      <td>
        <button class="btn btn-outline" style="padding: 4px 8px; font-size: 11.5px;" onclick="viewConversation('${c.id}')">View</button>
      </td>
    </tr>
  `).join('');
}

async function viewConversation(id) {
  try {
    const res = await fetch(`${API_BASE}/conversations/${id}`);
    if (res.ok) {
      const data = await res.json();
      const transcript = data.messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n\n---\n\n');
      alert(`Conversation Transcript for ${data.session_id}:\n\n` + transcript);
    }
  } catch (e) {
    alert('Failed to load conversation details.');
  }
}

function renderLeads() {
  const tbody = document.getElementById('leads-table-body');
  if (!tbody) return;

  if (!allLeads.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8;">No leads recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = allLeads.map(l => {
    let badgeClass = 'badge-new';
    if (l.status === 'qualified') badgeClass = 'badge-qualified';
    if (l.status === 'human_required' || l.human_required) badgeClass = 'badge-human';
    if (l.status === 'converted') badgeClass = 'badge-converted';

    return `
      <tr>
        <td><strong>${l.name || 'Anonymous Visitor'}</strong><br/><small style="color: #64748b;">${l.company || 'Direct Client'}</small></td>
        <td>
          ${l.email ? `📧 <a href="mailto:${l.email}">${l.email}</a><br/>` : ''}
          ${l.phone ? `📞 <a href="tel:${l.phone}">${l.phone}</a>` : '—'}
        </td>
        <td>
          <strong>${l.service || 'General Software'}</strong><br/>
          <small style="color: #64748b;">${l.requirement ? l.requirement.substring(0, 80) + '...' : 'Inquiry via chat'}</small>
        </td>
        <td><span class="badge ${badgeClass}">${l.status.toUpperCase()}</span></td>
        <td>${new Date(l.created_at).toLocaleDateString()}</td>
        <td>
          <select onchange="updateLeadStatus('${l.id}', this.value)" style="padding: 4px; border-radius: 6px; font-size: 12px;">
            <option value="new" ${l.status==='new'?'selected':''}>New</option>
            <option value="contacted" ${l.status==='contacted'?'selected':''}>Contacted</option>
            <option value="qualified" ${l.status==='qualified'?'selected':''}>Qualified</option>
            <option value="human_required" ${l.status==='human_required'?'selected':''}>Human Req</option>
            <option value="converted" ${l.status==='converted'?'selected':''}>Converted</option>
          </select>
        </td>
      </tr>
    `;
  }).join('');
}

async function updateLeadStatus(id, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/leads/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      await fetchLeads();
      updateKPIs();
    }
  } catch (e) {
    alert('Failed to update lead status');
  }
}

function filterLeads() {
  const filter = document.getElementById('lead-filter').value;
  if (!filter) {
    renderLeads();
    return;
  }
  const filtered = allLeads.filter(l => l.status === filter);
  const tbody = document.getElementById('leads-table-body');
  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8;">No leads with status '${filter}'.</td></tr>`;
    return;
  }
  // render subset
  const temp = allLeads;
  allLeads = filtered;
  renderLeads();
  allLeads = temp;
}

function renderKB() {
  const tbody = document.getElementById('kb-table-body');
  if (!tbody) return;

  if (!allDocuments.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">No indexed documents found.</td></tr>';
    return;
  }

  tbody.innerHTML = allDocuments.map(d => `
    <tr>
      <td><strong>${d.title}</strong></td>
      <td><a href="${d.url}" target="_blank" style="color: var(--primary); text-decoration: none;">${d.url}</a></td>
      <td>${(d.content_length / 1024).toFixed(1)} KB (${d.chunks_count || 1} chunks)</td>
      <td>${new Date(d.updated_at).toLocaleDateString()}</td>
    </tr>
  `).join('');
}

async function triggerReindex() {
  if (!confirm('Re-crawl and re-index the entire Techvunex knowledge base?')) return;
  alert('Re-indexing initiated in the background. Data will refresh shortly.');
  try {
    const res = await fetch(`${API_BASE}/kb/reindex`, { method: 'POST' });
    if (res.ok) {
      alert('Knowledge base reindexed successfully!');
      await loadAllData();
    }
  } catch (e) {
    alert('Re-indexing encountered an error.');
  }
}
