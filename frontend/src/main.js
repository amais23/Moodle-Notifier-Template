// ==========================================================================
// NTNU Moodle Notifier - Premium Web Dashboard Logic (Vanilla JS SPA)
// ==========================================================================

import './style.css';

import { 
  createIcons, 
  LayoutDashboard, 
  BookOpen, 
  ClipboardList, 
  Award, 
  Calendar, 
  MessageSquare, 
  LogOut, 
  ArrowRight, 
  Clock, 
  CheckCircle, 
  FolderOpen, 
  FileText, 
  FileEdit, 
  Presentation, 
  FileSpreadsheet, 
  Archive, 
  Image, 
  Video, 
  Music, 
  File, 
  RefreshCw, 
  X, 
  AlertCircle, 
  AlertTriangle,
  Check,
  Tag,
  Folder
} from 'lucide';

function renderIcons() {
  createIcons({
    icons: {
      LayoutDashboard, 
      BookOpen, 
      ClipboardList, 
      Award, 
      Calendar, 
      MessageSquare, 
      LogOut, 
      ArrowRight, 
      Clock, 
      CheckCircle, 
      FolderOpen, 
      FileText, 
      FileEdit, 
      Presentation, 
      FileSpreadsheet, 
      Archive, 
      Image, 
      Video, 
      Music, 
      File, 
      RefreshCw, 
      X, 
      AlertCircle, 
      AlertTriangle,
      Check,
      Tag,
      Folder
    }
  });
}

// Global state
const state = {
  token: localStorage.getItem('moodle_token') || '',
  userId: localStorage.getItem('moodle_user_id') || '',
  fullname: localStorage.getItem('moodle_fullname') || '',
  moodleUrl: localStorage.getItem('moodle_url') || 'https://moodle3.ntnu.edu.tw',
  activeCourseId: null
};

// API Helper
async function fetchAPI(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  if (state.moodleUrl) {
    headers['X-Moodle-Url'] = state.moodleUrl;
  }

  const response = await fetch(endpoint, {
    ...options,
    headers
  });

  if (response.status === 401 || response.status === 403) {
    // Session expired or invalid token
    logout();
    throw new Error('登入逾期或無效的憑證，請重新登入。');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `請求失敗 (${response.status})`);
  }

  return response.json();
}

// Authentication Functions
async function login(username, password, moodleUrl) {
  try {
    const data = await fetchAPI('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username, password, moodle_url: moodleUrl })
    });

    state.token = data.token;
    state.userId = data.user_id;
    state.fullname = data.fullname;
    state.moodleUrl = data.moodle_url || moodleUrl;

    localStorage.setItem('moodle_token', state.token);
    localStorage.setItem('moodle_user_id', state.userId);
    localStorage.setItem('moodle_fullname', state.fullname);
    localStorage.setItem('moodle_url', state.moodleUrl);

    window.location.hash = '#dashboard';
  } catch (error) {
    throw error;
  }
}

function logout() {
  state.token = '';
  state.userId = '';
  state.fullname = '';
  localStorage.removeItem('moodle_token');
  localStorage.removeItem('moodle_user_id');
  localStorage.removeItem('moodle_fullname');
  window.location.hash = '#login';
}

// Check auth state and redirect if needed
function checkAuth() {
  const hash = window.location.hash || '#dashboard';
  
  if (!state.token && hash !== '#login') {
    window.location.hash = '#login';
    return false;
  }
  
  if (state.token && hash === '#login') {
    window.location.hash = '#dashboard';
    return false;
  }

  return true;
}

// --- Views & Templates ---

const Layout = (contentHtml, activeRoute) => `
  <div class="layout-wrapper">
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="sidebar-logo">🎓</span>
        <span class="sidebar-brand">Moodle Notifier</span>
      </div>
      <div class="sidebar-profile">
        <div class="avatar">${state.fullname ? state.fullname.charAt(0) : 'U'}</div>
        <div class="profile-info">
          <span class="profile-name">${state.fullname || '使用者'}</span>
          <span class="profile-status">連線中</span>
        </div>
      </div>
      <nav class="sidebar-menu">
        <li class="menu-item ${activeRoute === 'dashboard' ? 'active' : ''}">
          <a href="#dashboard"><i data-lucide="layout-dashboard"></i>主頁概覽</a>
        </li>
        <li class="menu-item ${activeRoute === 'courses' ? 'active' : ''}">
          <a href="#courses"><i data-lucide="book-open"></i>我的課程</a>
        </li>
        <li class="menu-item ${activeRoute === 'assignments' ? 'active' : ''}">
          <a href="#assignments"><i data-lucide="clipboard-list"></i>作業列表</a>
        </li>
        <li class="menu-item ${activeRoute === 'grades' ? 'active' : ''}">
          <a href="#grades"><i data-lucide="award"></i>成績明細</a>
        </li>
        <li class="menu-item ${activeRoute === 'upcoming' ? 'active' : ''}">
          <a href="#upcoming"><i data-lucide="calendar"></i>行事曆</a>
        </li>
        <li class="menu-item ${activeRoute === 'messages' ? 'active' : ''}">
          <a href="#messages"><i data-lucide="message-square"></i>私訊通知</a>
        </li>
      </nav>
      <div class="sidebar-footer">
        <button class="btn btn-secondary btn-logout" id="btn-logout-sidebar">
          <i data-lucide="log-out"></i> 登出
        </button>
      </div>
    </aside>
    <main class="main-content">
      ${contentHtml}
    </main>
  </div>
`;

const Views = {
  login: () => `
    <div class="login-container">
      <div class="login-card glass-panel">
        <div class="login-header">
          <span class="login-logo">🎓</span>
          <h2 class="login-title">NTNU Moodle Notifier</h2>
          <p class="login-subtitle">登入以存取您的個人儀表板</p>
        </div>
        <div id="login-error-container"></div>
        <form id="login-form">
          <div class="input-group">
            <label class="input-label">Moodle 系統網址</label>
            <select class="input-field" id="login-url" required>
              <option value="https://moodle3.ntnu.edu.tw">moodle3.ntnu.edu.tw (預設)</option>
              <option value="https://moodle.ntnu.edu.tw">moodle.ntnu.edu.tw (新版)</option>
            </select>
          </div>
          <div class="input-group">
            <label class="input-label">師大 Portal 帳號</label>
            <input type="text" class="input-field" id="login-username" placeholder="請輸入學號或帳號" required autocomplete="username" />
          </div>
          <div class="input-group">
            <label class="input-label">密碼</label>
            <input type="password" class="input-field" id="login-password" placeholder="請輸入密碼" required autocomplete="current-password" />
          </div>
          <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 10px;" id="login-submit-btn">
            安全登入 <i data-lucide="arrow-right"></i>
          </button>
        </form>
      </div>
    </div>
  `,

  dashboard: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">哈囉，${state.fullname} 👋</h1>
          <p class="section-subtitle">歡迎回到 NTNU Moodle 主控台，以下是您的即時學習摘要</p>
        </div>
      </header>

      <!-- Stats Cards -->
      <div class="stats-grid" id="dashboard-stats">
        <div class="glass-panel stat-card shimmer">
          <div class="skeleton-text" style="width: 40px; height: 40px; border-radius: 8px;"></div>
          <div class="stat-info" style="width: 100%;">
            <div class="skeleton-text" style="width: 40px; height: 24px;"></div>
            <div class="skeleton-text" style="width: 80px; height: 14px;"></div>
          </div>
        </div>
        <div class="glass-panel stat-card shimmer">
          <div class="skeleton-text" style="width: 40px; height: 40px; border-radius: 8px;"></div>
          <div class="stat-info" style="width: 100%;">
            <div class="skeleton-text" style="width: 40px; height: 24px;"></div>
            <div class="skeleton-text" style="width: 80px; height: 14px;"></div>
          </div>
        </div>
        <div class="glass-panel stat-card shimmer">
          <div class="skeleton-text" style="width: 40px; height: 40px; border-radius: 8px;"></div>
          <div class="stat-info" style="width: 100%;">
            <div class="skeleton-text" style="width: 40px; height: 24px;"></div>
            <div class="skeleton-text" style="width: 80px; height: 14px;"></div>
          </div>
        </div>
      </div>

      <div class="dashboard-details">
        <!-- Upcoming assignments -->
        <div class="glass-panel" style="display: flex; flex-direction: column;">
          <div class="panel-header">
            <span class="panel-title"><i data-lucide="clock" style="color: var(--primary-light)"></i> 即將截止作業</span>
            <a href="#assignments" class="btn btn-secondary" style="font-size: 0.8rem; padding: 6px 12px;">查看所有</a>
          </div>
          <div class="panel-body" id="dashboard-assignments">
            <div class="shimmer skeleton-text" style="height: 50px; margin-bottom: 12px; border-radius: 8px;"></div>
            <div class="shimmer skeleton-text" style="height: 50px; margin-bottom: 12px; border-radius: 8px;"></div>
          </div>
        </div>

        <!-- Recent upcoming events -->
        <div class="glass-panel" style="display: flex; flex-direction: column;">
          <div class="panel-header">
            <span class="panel-title"><i data-lucide="calendar" style="color: var(--secondary-light)"></i> 近期行事曆</span>
          </div>
          <div class="panel-body" id="dashboard-calendar">
            <div class="shimmer skeleton-text" style="height: 40px; margin-bottom: 12px; border-radius: 8px;"></div>
            <div class="shimmer skeleton-text" style="height: 40px; margin-bottom: 12px; border-radius: 8px;"></div>
          </div>
        </div>
      </div>
    </div>
  `, 'dashboard'),

  courses: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">我的課程</h1>
          <p class="section-subtitle">點擊課程卡片可展開課程章節與教材檔案</p>
        </div>
      </header>
      <div class="courses-grid" id="courses-container">
        <!-- Skeleton loaders -->
        <div class="glass-panel course-card shimmer" style="height: 220px;"></div>
        <div class="glass-panel course-card shimmer" style="height: 220px;"></div>
        <div class="glass-panel course-card shimmer" style="height: 220px;"></div>
      </div>
    </div>
  `, 'courses'),

  courseDetails: (courseId) => Layout(`
    <div class="content-section">
      <header class="section-header" style="margin-bottom: 20px;">
        <div>
          <button class="btn btn-secondary" style="padding: 6px 12px; margin-bottom: 12px;" onclick="window.location.hash='#courses'">
            <i data-lucide="arrow-left"></i> 返回課程列表
          </button>
          <h1 class="section-title" id="course-detail-title">課程單元教材</h1>
        </div>
      </header>
      <div id="course-detail-content">
        <div class="loading-container">
          <div class="spinner"></div>
          <span>正在加載課程教材...</span>
        </div>
      </div>
    </div>
  `, 'courses'),

  assignments: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">作業清單</h1>
          <p class="section-subtitle">點擊作業查看即時繳交狀態與評分回饋</p>
        </div>
      </header>
      <div class="list-container" id="assignments-container">
        <div class="glass-panel list-item shimmer" style="height: 80px;"></div>
        <div class="glass-panel list-item shimmer" style="height: 80px;"></div>
      </div>
    </div>
  `, 'assignments'),

  grades: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">成績明細</h1>
          <p class="section-subtitle">選擇課程查看您在該門課的成績分配與排名</p>
        </div>
      </header>
      
      <div class="glass-panel" style="margin-bottom: 24px; padding: 20px; display: flex; align-items: center; gap: 16px;">
        <label class="input-label" style="margin-bottom: 0;">選擇課程：</label>
        <select class="input-field" id="grades-course-select" style="max-width: 320px;">
          <option value="">請載入中...</option>
        </select>
      </div>

      <div class="glass-panel" style="overflow-x: auto;" id="grades-table-container">
        <div class="empty-state">
          <i data-lucide="award"></i>
          <span>請從上方下拉選單選擇一門課程以查看成績</span>
        </div>
      </div>
    </div>
  `, 'grades'),

  upcoming: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">行事曆待辦事項</h1>
          <p class="section-subtitle">即將到來的課程活動、測驗或作業截止時間</p>
        </div>
      </header>
      <div class="list-container" id="upcoming-container">
        <div class="glass-panel list-item shimmer" style="height: 60px;"></div>
        <div class="glass-panel list-item shimmer" style="height: 60px;"></div>
      </div>
    </div>
  `, 'upcoming'),

  messages: () => Layout(`
    <div class="content-section">
      <header class="section-header">
        <div>
          <h1 class="section-title">私訊通知</h1>
          <p class="section-subtitle">查看來自教授、助教或同學的最新 Moodle 站內訊息</p>
        </div>
      </header>
      <div class="glass-panel chat-container" id="messages-container">
        <div class="chat-sidebar" id="chat-users-list">
          <div style="padding: 20px; text-align: center; color: var(--text-muted);">載入對話中...</div>
        </div>
        <div class="chat-main-area" id="chat-main-area">
          <div class="empty-state" style="margin-top: 15%;">
            <i data-lucide="message-square"></i>
            <span>請選擇左側聯絡人以查看詳細對話</span>
          </div>
        </div>
      </div>
    </div>
  `, 'messages')
};

// --- Page Render Functions ---

// 1. Dashboard Render
async function renderDashboard() {
  try {
    // Parallel load necessary data to speed up
    const [summary, upcoming, assignments] = await Promise.all([
      fetchAPI('/api/dashboard/summary').catch(() => ({ unread_messages: 0, upcoming_events: 0, pending_assignments: 0 })),
      fetchAPI('/api/upcoming').catch(() => []),
      fetchAPI('/api/assignments').catch(() => [])
    ]);

    // Stats HTML
    const statsContainer = document.getElementById('dashboard-stats');
    if (statsContainer) {
      statsContainer.innerHTML = `
        <div class="glass-panel stat-card glass-panel-interactive">
          <div class="stat-icon primary"><i data-lucide="clipboard-list"></i></div>
          <div class="stat-info">
            <span class="stat-value">${summary.pending_assignments}</span>
            <span class="stat-label">未繳作業</span>
          </div>
        </div>
        <div class="glass-panel stat-card glass-panel-interactive">
          <div class="stat-icon accent"><i data-lucide="message-square"></i></div>
          <div class="stat-info">
            <span class="stat-value">${summary.unread_messages}</span>
            <span class="stat-label">未讀私訊</span>
          </div>
        </div>
        <div class="glass-panel stat-card glass-panel-interactive">
          <div class="stat-icon cyan"><i data-lucide="calendar"></i></div>
          <div class="stat-info">
            <span class="stat-value">${summary.upcoming_events}</span>
            <span class="stat-label">即將截止事項</span>
          </div>
        </div>
      `;
    }

    // Upcoming assignments rendering (max 3)
    const assignContainer = document.getElementById('dashboard-assignments');
    if (assignContainer) {
      // Filter out assignments that are already submitted or ended
      const pendingList = assignments.slice(0, 3);
      if (pendingList.length === 0) {
        assignContainer.innerHTML = `
          <div class="empty-state">
            <i data-lucide="check-circle" style="color: var(--color-success)"></i>
            <span>太棒了！目前沒有即將截止的作業</span>
          </div>
        `;
      } else {
        assignContainer.innerHTML = `
          <div class="list-container">
            ${pendingList.map(a => {
              const dueTimeStr = new Date(a.duedate * 1000).toLocaleString('zh-TW', { hour12: false });
              const isPast = a.duedate * 1000 < Date.now();
              return `
                <div class="list-item glass-panel" style="padding: 12px 16px;">
                  <div class="item-main">
                    <span class="item-course">${a.course_name || '課程'}</span>
                    <span class="item-title" style="font-size: 0.95rem;">${a.name}</span>
                    <span class="item-meta" style="font-size: 0.8rem;">
                      <span><i data-lucide="clock"></i> 截止：${dueTimeStr}</span>
                    </span>
                  </div>
                  <span class="status-badge ${isPast ? 'danger' : 'warning'}">
                    ${isPast ? '已截止' : '待繳交'}
                  </span>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }
    }

    // Calendar events rendering (max 4)
    const calContainer = document.getElementById('dashboard-calendar');
    if (calContainer) {
      const items = upcoming.slice(0, 4);
      if (items.length === 0) {
        calContainer.innerHTML = `
          <div class="empty-state">
            <i data-lucide="calendar"></i>
            <span>本週無行事曆事項</span>
          </div>
        `;
      } else {
        calContainer.innerHTML = `
          <div class="list-container">
            ${items.map(e => {
              const timeStr = new Date(e.timesort * 1000).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' });
              return `
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.03);">
                  <span style="font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%;">${e.name}</span>
                  <span style="font-size: 0.8rem; color: var(--secondary-light); font-weight: 500;">${timeStr}</span>
                </div>
              `;
            }).join('')}
          </div>
        `;
      }
    }

    renderIcons();
  } catch (error) {
    console.error(error);
  }
}

// 2. Courses Render
async function renderCourses() {
  try {
    const courses = await fetchAPI('/api/courses');
    const container = document.getElementById('courses-container');
    
    if (container) {
      if (courses.length === 0) {
        container.innerHTML = `
          <div class="glass-panel" style="grid-column: 1 / -1; padding: 40px; text-align: center;">
            <i data-lucide="book-open" style="font-size: 2.5rem; color: var(--text-dimmed);"></i>
            <p style="margin-top: 12px; color: var(--text-muted);">目前無任何課程資料</p>
          </div>
        `;
      } else {
        container.innerHTML = courses.map(c => `
          <div class="glass-panel glass-panel-interactive course-card" onclick="window.location.hash = '#courses/${c.id}'">
            <div class="course-banner">
              <span class="course-code">${c.shortname || 'Course'}</span>
            </div>
            <div class="course-info">
              <h3 class="course-name">${c.fullname}</h3>
              <div class="course-meta">
                <span>學期：${state.moodleUrl.includes('moodle3') ? '舊學期' : '本學期'}</span>
              </div>
            </div>
          </div>
        `).join('');
      }
      renderIcons();
    }
  } catch (error) {
    const container = document.getElementById('courses-container');
    if (container) {
      container.innerHTML = `<div class="glass-panel" style="grid-column: 1/-1; padding: 24px; color: var(--color-danger);">載入課程失敗: ${error.message}</div>`;
    }
  }
}

// 3. Course Details Render (Chapters & Files)
async function renderCourseDetails(courseId) {
  const container = document.getElementById('course-detail-content');
  try {
    const data = await fetchAPI(`/api/courses/${courseId}/contents`);
    
    // Find course title
    const courses = await fetchAPI('/api/courses').catch(() => []);
    const currentCourse = courses.find(c => c.id === parseInt(courseId));
    if (currentCourse) {
      document.getElementById('course-detail-title').innerText = currentCourse.fullname;
    }

    if (data.length === 0) {
      container.innerHTML = `
        <div class="glass-panel empty-state">
          <i data-lucide="folder-open"></i>
          <span>此課程目前尚無章節單元內容</span>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="course-detail-view">
          ${data.map(chapter => {
            // Filter modules to files, URLs and assignments
            const modules = chapter.modules || [];
            const validModules = modules.filter(m => ['resource', 'url', 'assign', 'forum', 'folder'].includes(m.modname));
            
            if (validModules.length === 0) return ''; // Skip empty chapters

            return `
              <div class="chapter-card glass-panel">
                <div class="chapter-header">${chapter.name}</div>
                <div class="chapter-body">
                  <ul class="resource-list">
                    ${validModules.map(m => {
                      let icon = 'file';
                      let url = '#';
                      let extraAttr = '';

                      if (m.modname === 'assign') {
                        icon = 'file-edit';
                        url = `#assignments`;
                      } else if (m.modname === 'forum') {
                        icon = 'message-square';
                      } else if (m.modname === 'url') {
                        icon = 'link';
                        url = m.url;
                        extraAttr = 'target="_blank"';
                      } else if (m.modname === 'resource' && m.contents && m.contents.length > 0) {
                        const file = m.contents[0];
                        icon = getFileIcon(file.filename);
                        // Proxy Download API
                        url = `/api/download?url=${encodeURIComponent(file.fileurl)}`;
                        extraAttr = `download="${file.filename}" target="_blank"`;
                      } else if (m.modname === 'folder') {
                        icon = 'folder';
                      }

                      return `
                        <li class="resource-item">
                          <a href="${url}" ${extraAttr} class="resource-link">
                            <i data-lucide="${icon}"></i>
                            <span>${m.name}</span>
                          </a>
                          <span style="font-size: 0.75rem; color: var(--text-dimmed);">
                            ${m.modname === 'resource' && m.contents && m.contents[0].filesize 
                              ? formatBytes(m.contents[0].filesize) 
                              : m.modname.toUpperCase()}
                          </span>
                        </li>
                      `;
                    }).join('')}
                  </ul>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }
    renderIcons();
  } catch (error) {
    container.innerHTML = `<div class="glass-panel" style="padding: 24px; color: var(--color-danger);">載入課程明細失敗: ${error.message}</div>`;
  }
}

// 4. Assignments Render
async function renderAssignments() {
  const container = document.getElementById('assignments-container');
  try {
    const assignments = await fetchAPI('/api/assignments');
    
    if (assignments.length === 0) {
      container.innerHTML = `
        <div class="glass-panel empty-state">
          <i data-lucide="check-circle" style="color: var(--color-success)"></i>
          <span>目前無任何作業</span>
        </div>
      `;
    } else {
      container.innerHTML = assignments.map(a => {
        const dueTimeStr = new Date(a.duedate * 1000).toLocaleString('zh-TW', { hour12: false });
        const isPast = a.duedate * 1000 < Date.now();
        
        return `
          <div class="glass-panel list-item glass-panel-interactive" id="assign-item-${a.id}">
            <div class="item-main">
              <span class="item-course">${a.course_name}</span>
              <span class="item-title">${a.name}</span>
              <span class="item-meta">
                <span><i data-lucide="calendar"></i> 截止日：${dueTimeStr}</span>
                <span id="assign-status-text-${a.id}" class="status-badge info" style="cursor: pointer; padding: 2px 8px; font-size: 0.75rem;" onclick="loadSubmissionStatus(${a.id})">
                  <i data-lucide="refresh-cw" style="width:12px;height:12px;animation:spin 2s linear infinite;"></i> 載入繳交狀態
                </span>
              </span>
            </div>
            <div>
              <span class="status-badge ${isPast ? 'danger' : 'warning'}" id="assign-badge-${a.id}">
                ${isPast ? '已截止' : '待繳交'}
              </span>
            </div>
          </div>
        `;
      }).join('');
      renderIcons();
      
      // Auto-trigger loading submission status for the first 3 assignments to make it responsive
      const autoLoadCount = Math.min(assignments.length, 3);
      for (let i = 0; i < autoLoadCount; i++) {
        loadSubmissionStatus(assignments[i].id);
      }
    }
  } catch (error) {
    container.innerHTML = `<div class="glass-panel" style="padding: 24px; color: var(--color-danger);">載入作業失敗: ${error.message}</div>`;
  }
}

// Fetch single assignment status
async function loadSubmissionStatus(assignId) {
  const badgeEl = document.getElementById(`assign-badge-${assignId}`);
  const statusEl = document.getElementById(`assign-status-text-${assignId}`);
  
  if (!statusEl) return;
  
  try {
    statusEl.innerHTML = `<i data-lucide="refresh-cw" style="width:12px;height:12px;animation:spin 2s linear infinite;"></i> 查詢中...`;
    renderIcons();

    const data = await fetchAPI(`/api/assignments/${assignId}/status`);
    // Parse response
    const lastSub = data.lastattempt || {};
    const submission = lastSub.submission || {};
    const status = submission.status || 'new'; // 'submitted', 'new', 'draft'

    if (status === 'submitted') {
      statusEl.className = 'status-badge success';
      statusEl.innerHTML = `<i data-lucide="check"></i> 已繳交`;
      if (badgeEl) {
        badgeEl.className = 'status-badge success';
        badgeEl.innerText = '已繳交';
      }
    } else if (status === 'draft') {
      statusEl.className = 'status-badge warning';
      statusEl.innerHTML = `<i data-lucide="alert-circle"></i> 草稿 (未送出)`;
      if (badgeEl) {
        badgeEl.className = 'status-badge warning';
        badgeEl.innerText = '未完成';
      }
    } else {
      statusEl.className = 'status-badge danger';
      statusEl.innerHTML = `<i data-lucide="x"></i> 未繳交`;
    }
    
    // Add grading status if graded
    const feedback = data.feedback || {};
    const grade = feedback.grade || {};
    if (grade.grade) {
      statusEl.innerHTML += ` | 已評分: <span class="grade-val">${grade.grade}分</span>`;
    }

    renderIcons();
  } catch (error) {
    statusEl.className = 'status-badge danger';
    statusEl.innerHTML = `查詢失敗`;
  }
}

// 5. Grades Render
async function renderGrades() {
  try {
    const courses = await fetchAPI('/api/courses');
    const selectEl = document.getElementById('grades-course-select');
    
    if (selectEl) {
      if (courses.length === 0) {
        selectEl.innerHTML = '<option value="">無可用課程</option>';
        return;
      }

      selectEl.innerHTML = '<option value="">-- 請選擇課程 --</option>' + 
        courses.map(c => `<option value="${c.id}">${c.fullname}</option>`).join('');
      
      selectEl.addEventListener('change', async (e) => {
        const courseId = e.target.value;
        const tableContainer = document.getElementById('grades-table-container');
        
        if (!courseId) {
          tableContainer.innerHTML = `
            <div class="empty-state">
              <i data-lucide="award"></i>
              <span>請從上方下拉選單選擇一門課程以查看成績</span>
            </div>
          `;
          renderIcons();
          return;
        }

        tableContainer.innerHTML = `
          <div class="loading-container">
            <div class="spinner"></div>
            <span>正在取得成績明細...</span>
          </div>
        `;

        try {
          const grades = await fetchAPI(`/api/grades/${courseId}`);
          if (grades.length === 0) {
            tableContainer.innerHTML = `
              <div class="empty-state">
                <i data-lucide="info"></i>
                <span>此課程目前尚無評分項目</span>
              </div>
            `;
          } else {
            tableContainer.innerHTML = `
              <table class="grades-table">
                <thead>
                  <tr>
                    <th>項目名稱</th>
                    <th>成績</th>
                    <th>範圍</th>
                    <th>百分比</th>
                    <th>回饋評語</th>
                  </tr>
                </thead>
                <tbody>
                  ${grades.map(g => {
                    if (g.itemtype === 'course') return ''; // Skip final summary item row for clean view
                    const gradeStr = g.graderaw !== null ? g.graderaw : '尚未評分';
                    const percentage = g.percentageformatted || '-';
                    const feedback = g.feedback || '-';
                    return `
                      <tr>
                        <td><strong>${g.itemname || '總成績'}</strong></td>
                        <td><span class="grade-val">${gradeStr}</span></td>
                        <td>${g.grademin} - ${g.grademax}</td>
                        <td><span class="grade-percentage">${percentage}</span></td>
                        <td style="font-size: 0.85rem; color: var(--text-muted); max-width: 250px;">${feedback}</td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            `;
          }
          renderIcons();
        } catch (err) {
          tableContainer.innerHTML = `<div style="padding: 24px; color: var(--color-danger);">載入成績失敗: ${err.message}</div>`;
        }
      });
    }
  } catch (error) {
    console.error(error);
  }
}

// 6. Upcoming Events Render
async function renderUpcoming() {
  const container = document.getElementById('upcoming-container');
  try {
    const events = await fetchAPI('/api/upcoming');
    
    if (events.length === 0) {
      container.innerHTML = `
        <div class="glass-panel empty-state">
          <i data-lucide="check-circle" style="color: var(--color-success)"></i>
          <span>目前無任何即將到來的行事曆事件</span>
        </div>
      `;
    } else {
      container.innerHTML = events.map(e => {
        const timeStr = new Date(e.timesort * 1000).toLocaleString('zh-TW', { hour12: false });
        return `
          <div class="glass-panel list-item glass-panel-interactive">
            <div class="item-main">
              <span class="item-course">${e.course ? e.course.fullname : '系統行事曆'}</span>
              <span class="item-title">${e.name}</span>
              <span class="item-meta">
                <span><i data-lucide="clock"></i> 時間：${timeStr}</span>
                <span><i data-lucide="tag"></i> 類型：${e.eventtype.toUpperCase()}</span>
              </span>
            </div>
            <div>
              <span class="status-badge info">
                ${e.modulename ? e.modulename.toUpperCase() : 'EVENT'}
              </span>
            </div>
          </div>
        `;
      }).join('');
      renderIcons();
    }
  } catch (error) {
    container.innerHTML = `<div class="glass-panel" style="padding: 24px; color: var(--color-danger);">載入行事曆失敗: ${error.message}</div>`;
  }
}

// 7. Messages Render
async function renderMessages() {
  const usersListEl = document.getElementById('chat-users-list');
  try {
    const conversations = await fetchAPI('/api/messages');
    
    if (conversations.length === 0) {
      usersListEl.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted);">無任何私訊對話紀錄</div>';
      return;
    }

    usersListEl.innerHTML = conversations.map(c => {
      const member = c.members[0] || {};
      const lastMsg = c.messages[0] || {};
      const isUnread = c.unreadcount > 0;
      const timeStr = lastMsg.timecreated 
        ? new Date(lastMsg.timecreated * 1000).toLocaleDateString('zh-TW', { month: 'numeric', day: 'numeric' }) 
        : '';
        
      return `
        <div class="chat-list-item" id="chat-user-${c.id}" onclick="loadConversationDetail(${c.id}, '${member.fullname}')">
          <div class="avatar" style="width: 36px; height: 36px; font-size: 0.95rem;">${member.fullname ? member.fullname.charAt(0) : 'U'}</div>
          <div class="chat-user-info">
            <span class="chat-username">${member.fullname}</span>
            <span class="chat-preview">${lastMsg.text || '無訊息內容'}</span>
          </div>
          <div style="display:flex; flex-direction:column; align-items:flex-end; gap: 4px;">
            <span class="chat-time">${timeStr}</span>
            ${isUnread ? `<span style="background:var(--primary); color:white; font-size:0.7rem; font-weight:700; padding:2px 6px; border-radius:10px;">${c.unreadcount}</span>` : ''}
          </div>
        </div>
      `;
    }).join('');

  } catch (error) {
    usersListEl.innerHTML = `<div style="padding: 20px; color: var(--color-danger);">載入對話列表失敗: ${error.message}</div>`;
  }
}

// Load conversation details
async function loadConversationDetail(convId, otherName) {
  // Highlight active user
  document.querySelectorAll('.chat-list-item').forEach(el => el.classList.remove('active'));
  document.getElementById(`chat-user-${convId}`).classList.add('active');

  const mainAreaEl = document.getElementById('chat-main-area');
  mainAreaEl.innerHTML = `
    <div class="chat-main-header">
      <div class="avatar" style="width: 32px; height: 32px; font-size: 0.9rem;">${otherName.charAt(0)}</div>
      <span class="chat-username">${otherName}</span>
    </div>
    <div class="chat-message-list" id="chat-messages-container">
      <div style="display:flex; justify-content:center; align-items:center; height:100%;">
        <div class="spinner"></div>
      </div>
    </div>
  `;

  try {
    // API endpoint doesn't exist directly for detail in our basic router but we can fetch messages list or parse from the main conversations list
    // In our simplified backend, we return messages inside conversation payload.
    const conversations = await fetchAPI('/api/messages');
    const currentConv = conversations.find(c => c.id === convId) || {};
    const messages = currentConv.messages || [];

    const msgContainer = document.getElementById('chat-messages-container');
    if (messages.length === 0) {
      msgContainer.innerHTML = '<div style="text-align:center; padding: 24px; color: var(--text-muted);">無任何訊息</div>';
      return;
    }

    // Sort messages ascending by time
    const sortedMsgs = [...messages].reverse();

    msgContainer.innerHTML = sortedMsgs.map(m => {
      const isOutgoing = m.useridfrom === parseInt(state.userId);
      const timeStr = new Date(m.timecreated * 1000).toLocaleString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });
      
      return `
        <div class="msg-bubble ${isOutgoing ? 'outgoing' : 'incoming'}">
          <div>${m.text}</div>
          <div class="msg-meta">${timeStr}</div>
        </div>
      `;
    }).join('');

    // Scroll to bottom
    msgContainer.scrollTop = msgContainer.scrollHeight;

  } catch (err) {
    document.getElementById('chat-messages-container').innerHTML = `<div style="padding: 24px; color: var(--color-danger);">載入訊息失敗: ${err.message}</div>`;
  }
}

// --- Helper Utilities ---

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  if (['pdf'].includes(ext)) return 'file-text';
  if (['doc', 'docx'].includes(ext)) return 'file-edit';
  if (['ppt', 'pptx'].includes(ext)) return 'presentation';
  if (['xls', 'xlsx'].includes(ext)) return 'file-spreadsheet';
  if (['zip', 'rar', '7z'].includes(ext)) return 'archive';
  if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) return 'image';
  if (['mp4', 'avi', 'mkv'].includes(ext)) return 'video';
  if (['mp3', 'wav'].includes(ext)) return 'music';
  return 'file';
}

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}


// ==========================================================================
// SPA ROUTER & ENTRY POINT
// ==========================================================================

async function router() {
  if (!checkAuth()) return;

  const appEl = document.getElementById('app');
  let hash = window.location.hash || '#dashboard';

  // Support course parameter routes like #courses/12345
  if (hash.startsWith('#courses/')) {
    const courseId = hash.split('/')[1];
    appEl.innerHTML = Views.courseDetails(courseId);
    renderIcons();
    setupSidebarEvents();
    await renderCourseDetails(courseId);
    return;
  }

  // Normal routes
  switch (hash) {
    case '#login':
      appEl.innerHTML = Views.login();
      setupLoginEvents();
      break;
    case '#dashboard':
      appEl.innerHTML = Views.dashboard();
      setupSidebarEvents();
      await renderDashboard();
      break;
    case '#courses':
      appEl.innerHTML = Views.courses();
      setupSidebarEvents();
      await renderCourses();
      break;
    case '#assignments':
      appEl.innerHTML = Views.assignments();
      setupSidebarEvents();
      await renderAssignments();
      break;
    case '#grades':
      appEl.innerHTML = Views.grades();
      setupSidebarEvents();
      await renderGrades();
      break;
    case '#upcoming':
      appEl.innerHTML = Views.upcoming();
      setupSidebarEvents();
      await renderUpcoming();
      break;
    case '#messages':
      appEl.innerHTML = Views.messages();
      setupSidebarEvents();
      await renderMessages();
      break;
    default:
      appEl.innerHTML = `<div style="padding: 40px; text-align:center;"><h2>404 - 找不到網頁</h2><a href="#dashboard">返回主頁</a></div>`;
  }
  
  renderIcons();
}

// Event Listeners Setups

function setupLoginEvents() {
  const form = document.getElementById('login-form');
  const errorContainer = document.getElementById('login-error-container');
  const submitBtn = document.getElementById('login-submit-btn');

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value;
      const moodleUrl = document.getElementById('login-url').value;

      try {
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i data-lucide="refresh-cw" style="animation: spin 2s linear infinite;"></i> 登入中...`;
        renderIcons();
        errorContainer.innerHTML = '';

        await login(username, password, moodleUrl);
      } catch (err) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `安全登入 <i data-lucide="arrow-right"></i>`;
        renderIcons();
        
        errorContainer.innerHTML = `
          <div class="login-error">
            <i data-lucide="alert-triangle"></i>
            <span>${err.message || '登入失敗，請檢查帳號密碼與網路連線。'}</span>
          </div>
        `;
        renderIcons();
      }
    });
  }
}

function setupSidebarEvents() {
  const logoutBtn = document.getElementById('btn-logout-sidebar');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  }
}

// Global functions exports for HTML inline onclick handlers
window.loadSubmissionStatus = loadSubmissionStatus;
window.loadConversationDetail = loadConversationDetail;

// Start app
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', router);
