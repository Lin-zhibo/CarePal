// ======================== 后端地址统一配置（只改这里） ========================
// 改 IP 时，只需要修改 BACKEND_SERVER.host。
// 改端口时，只需要修改 BACKEND_SERVER.port。
const BACKEND_SERVER = Object.freeze({
  protocol: 'http',
  host: '192.168.137.79',
  port: 8000,
})

// 开发环境优先走 Vite 代理前缀，避免浏览器跨域预检导致 405。
const DEV_API_BASE = '/api'

// 生产环境直连后端地址。
const PROD_API_BASE = `${BACKEND_SERVER.protocol}://${BACKEND_SERVER.host}:${BACKEND_SERVER.port}`

const MONITOR_SERVER = Object.freeze({
  protocol: 'http',
  host: BACKEND_SERVER.host,
  port: 8010,
})

const DEV_MONITOR_API_BASE = '/yoloapi'
const PROD_MONITOR_API_BASE = `${MONITOR_SERVER.protocol}://${MONITOR_SERVER.host}:${MONITOR_SERVER.port}`

export const APP_CONFIG = Object.freeze({
  APP_NAME: 'CarePal',
  APP_TITLE: 'CarePal 康伴 · 健康控制台',

  // 当前前端实际使用的 API 基础地址：
  // 1) 开发环境：走 /api 代理
  // 2) 生产环境：直连 protocol://host:port
  API_BASE_URL: import.meta.env.DEV ? DEV_API_BASE : PROD_API_BASE,

  // 仅用于展示与排查，业务请求仍以 API_BASE_URL 为准。
  BACKEND_SERVER,
  MONITOR_SERVER,
  MONITOR_API_BASE: import.meta.env.DEV ? DEV_MONITOR_API_BASE : PROD_MONITOR_API_BASE,

  API_PATHS: Object.freeze({
    health: '/health',
    login: '/auth/login',
    register: '/auth/register',
    chatText: '/chat/text',
    chatVoice: '/chat/voice',
    chatVoiceFilePrefix: '/chat/voice/file/',
    ocrAnalyze: '/ocr/analyze',
    monitorDetectFrame: '/detect/frame',
  }),

  PROMPT_IDS: Object.freeze({
    chatAssistant: 1,
    weeklyAssistant: 2,
  }),

  CHAT_OPTIONS: Object.freeze({
    withText: true,
    withAudio: true,
  }),

  WEEKLY_OPTIONS: Object.freeze({
    withText: true,
    withAudio: false,
  }),

  // 页面默认状态
  DEFAULTS: Object.freeze({
    currentModule: 'chat',
    profile: Object.freeze({
      avatar: '',
      name: '康复小伙伴',
      phone: '13800000000',
      emergencyName: '',
      emergencyPhone: '',
    }),
    moduleList: Object.freeze([
      Object.freeze({ key: 'chat', label: '对话', desc: '与 AI 对话，解读用药与康复', icon: '/static/icons/chat.svg' }),
      Object.freeze({ key: 'schedule', label: '日程表', desc: '查看今日用药与训练安排', icon: '/static/icons/schedule.svg' }),
      Object.freeze({ key: 'weekly-report', label: '周报告', desc: '完成周度问卷，生成康复总结', icon: '/static/icons/schedule.svg' }),
      Object.freeze({ key: 'ocr', label: 'OCR 识别', desc: '拍照识别药盒与说明书', icon: '/static/icons/ocr.svg' }),
      Object.freeze({ key: 'profile', label: '我的', desc: '账号与提醒偏好设置', icon: '/static/icons/profile.svg' }),
    ]),
  }),

  // 文本输入限制
  INPUT_LIMITS: Object.freeze({
    chatMessageMaxLength: 300,
    weeklyNoteMaxLength: 1000,
    phoneMaxLength: 11,
    emergencyPhoneMaxLength: 11,
  }),

  // 鉴权规则
  AUTH_RULES: Object.freeze({
    usernameMaxLength: 32,
    passwordMaxLength: 64,
    passwordMinLength: 7,
  }),

  // 本地缓存键
  STORAGE_KEYS: Object.freeze({
    accessToken: 'carepal_access_token',
    authUsername: 'carepal_auth_username',
    profile: 'carepal_profile',
    elderMode: 'carepal_elderMode',
    darkMode: 'carepal_darkMode',
    chatHistoryPrefix: 'carepal_chat_history_',
    voiceDbName: 'carepal_voice_db',
    voiceDbStore: 'voice_blobs',
  }),

  // 对话历史持久化配置
  CHAT_HISTORY: Object.freeze({
    maxMessages: 80,
  }),

  // 录音配置
  RECORDER: Object.freeze({
    fallbackDelayMs: 1200,
    minTapIntervalMs: 450,
    uni: Object.freeze({
      duration: 60000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000,
      format: 'mp3',
      frameSize: 50,
    }),
    media: Object.freeze({
      preferredMimeTypes: Object.freeze([
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ]),
      defaultBlobType: 'audio/webm',
    }),
  }),

  // 音频上传/选择配置
  AUDIO: Object.freeze({
    chooseFileExtensions: Object.freeze(['mp3', 'wav', 'm4a']),
    uploadFieldName: 'audio',
    withTextFieldName: 'with_text',
    withTextValue: 'true',
    defaultWebmFileNamePrefix: 'voice_',
    defaultMp3FileNamePrefix: 'voice_',
  }),

  // OCR 配置
  OCR: Object.freeze({
    // OCR 上传与识别请求超时（毫秒）：5分钟
    requestTimeoutMs: 5 * 60 * 1000,
    chooseImageCount: 1,
    chooseImageSizeType: Object.freeze(['compressed']),
    chooseImageSourceTypes: Object.freeze(['album', 'camera']),
    cameraOnlySourceType: Object.freeze(['camera']),
    albumOnlySourceType: Object.freeze(['album']),
    cameraIdealWidth: 1280,
    cameraIdealHeight: 720,
  }),

  // 日历配置
  CALENDAR: Object.freeze({
    weekdays: Object.freeze(['一', '二', '三', '四', '五', '六', '日']),
  }),

  // 问卷配置
  WEEKLY: Object.freeze({
    questionCount: 7,
    minScore: 0,
    maxScore: 4,
  }),
})
