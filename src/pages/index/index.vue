<template>
  <view :class="['carepal-page', elderMode ? 'is-elder' : '', darkMode ? 'is-dark' : '']">
    <view class="carepal-header">
      <view class="carepal-header-left">
        <view class="carepal-header-brand">
          <view class="carepal-header-logo">
            <image class="carepal-header-logo-image" src="/static/img/logo.png" mode="aspectFit" />
          </view>
          <view class="carepal-header-title-wrap">
            <view class="carepal-header-title">CarePal康伴</view>
            <view class="carepal-header-subtitle">智能康复陪伴平台</view>
          </view>
        </view>
      </view>
      <view class="carepal-header-right">
        <view class="carepal-header-chip">当前模块 · {{ currentModuleLabel }}</view>
        <view class="carepal-header-user">
          <view class="carepal-header-user-dot"></view>
          <view>您好，欢迎使用</view>
        </view>
      </view>
    </view>

    <view class="carepal-shell">
      <view :class="['carepal-main', sidebarExpanded ? 'is-sidebar-expanded' : 'is-sidebar-collapsed']">
        <view class="carepal-sidebar-handle carepal-sidebar-handle--collapsed">
          <var-button
            size="small"
            plain
            class="carepal-sidebar-toggle carepal-sidebar-toggle--hint"
            @tap="toggleSidebar"
          >
            <view :class="['carepal-sidebar-toggle-icon', sidebarExpanded ? 'is-open' : '']"></view>
            <view class="carepal-sidebar-toggle-text">展开</view>
          </var-button>
        </view>
        <view class="carepal-main-left">
          <view class="carepal-sidebar">
            <view class="carepal-sidebar-handle carepal-sidebar-handle--expanded">
              <var-button
                size="small"
                plain
                class="carepal-sidebar-toggle carepal-sidebar-toggle--hint"
                @tap="toggleSidebar"
              >
                <view :class="['carepal-sidebar-toggle-icon', sidebarExpanded ? 'is-open' : '']"></view>
                <view class="carepal-sidebar-toggle-text">收起</view>
              </var-button>
            </view>
            <view class="carepal-sidebar-identity" @tap="openLoginDialog">
              <image
                class="carepal-sidebar-identity-avatar"
                :src="profile.avatar || '/static/icons/profile.svg'"
                mode="aspectFill"
              />
              <view class="carepal-sidebar-identity-text">
                <view class="carepal-sidebar-identity-name">{{ displayUserName }}</view>
                <view class="carepal-sidebar-identity-status">{{ loginStatusText }}</view>
              </view>
            </view>
            <view class="carepal-sidebar-title">功能模块</view>
            <var-button
              v-for="item in modules"
              :key="item.key"
              block
              :class="['carepal-nav-button', currentModule === item.key ? 'is-active' : '']"
              :type="currentModule === item.key ? 'primary' : 'default'"
              :color="
                currentModule === item.key
                  ? (darkMode
                    ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.46) 0%, rgba(147, 197, 253, 0.42) 50%, rgba(167, 243, 208, 0.4) 100%)'
                    : 'linear-gradient(135deg, #96cbff 0%, #aed9ff 48%, #c9ecff 100%)')
                  : (darkMode
                    ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.16) 0%, rgba(147, 197, 253, 0.14) 50%, rgba(167, 243, 208, 0.14) 100%)'
                    : 'linear-gradient(135deg, #f4faff 0%, #ecf6ff 55%, #f3fcff 100%)')
              "
              :text-color="
                currentModule === item.key
                  ? (darkMode ? '#f6fbff' : '#12426f')
                  : (darkMode ? '#e6eefc' : '#233a60')
              "
              @tap="onModuleChange(item.key)"
            >
              <view class="carepal-nav-content">
                <view
                  :class="['carepal-nav-icon-wrap', currentModule === item.key ? 'is-active' : '']"
                >
                  <image class="carepal-nav-icon" :src="item.icon" mode="aspectFit" />
                </view>
                <view class="carepal-nav-text">
                  <view class="carepal-nav-label">{{ item.label }}</view>
                  <view class="carepal-nav-desc">{{ item.desc }}</view>
                </view>
              </view>
            </var-button>
          </view>
        </view>

        <view class="carepal-main-right">
          <transition name="carepal-module" mode="out-in">
            <view :key="currentModule" class="carepal-module-stage">
          <!-- 模块 1：AI 对话 -->
          <view v-if="currentModule === 'chat'" class="carepal-chat">
            <view class="carepal-chat-header">
              <view class="carepal-chat-title">智能语音助手</view>
              <view class="carepal-chat-status">在线 · 为您解读用药与康复</view>
            </view>

            <view class="carepal-chat-body">
              <view
                v-for="msg in messages"
                :key="msg.id"
                :class="['carepal-chat-msg', msg.from === 'user' ? 'is-user' : 'is-ai']"
              >
                <view class="carepal-chat-avatar" v-if="msg.from === 'ai'">AI</view>
                <view class="carepal-chat-avatar carepal-chat-avatar--user" v-else>我</view>
                <view v-if="msg.kind === 'voice'" class="carepal-chat-voice-wrap" @tap="playMessageVoice(msg)">
                  <view class="carepal-chat-voice-bar">
                    <view class="carepal-chat-voice-icon">▶</view>
                    <view class="carepal-chat-voice-label">{{ msg.durationLabel || '语音消息' }}</view>
                    <view
                      v-if="msg.from === 'user'"
                      class="carepal-chat-voice-transcript-btn"
                      @tap.stop="toggleVoiceTranscript(msg)"
                    >
                      {{ msg.showTranscript ? '收起' : '转文字' }}
                    </view>
                  </view>
                  <view v-if="msg.showTranscript && msg.transcript" class="carepal-chat-voice-text">{{ msg.transcript }}</view>
                </view>
                <view v-else class="carepal-chat-bubble-wrap">
                  <view class="carepal-chat-bubble">{{ msg.text }}</view>
                  <view v-if="msg.from === 'ai'" class="carepal-chat-bubble-actions">
                    <view
                      class="carepal-chat-tts-btn"
                      @tap.stop="onPlayAiReply(msg)"
                    >
                      🔊
                    </view>
                    <view
                      class="carepal-chat-copy-btn"
                      @tap.stop="copyMessageText(msg)"
                      @longpress.stop="openCopyTextPanel(msg)"
                      title="复制"
                    >
                      ⧉
                    </view>
                  </view>
                </view>
              </view>
              <view v-if="showAiThinking" class="carepal-chat-msg is-ai">
                <view class="carepal-chat-avatar">AI</view>
                <view class="carepal-chat-bubble carepal-chat-bubble--loading">
                  <view class="carepal-chat-loading-text">AI 正在思考</view>
                  <view class="carepal-chat-loading-dots">
                    <view class="carepal-chat-loading-dot"></view>
                    <view class="carepal-chat-loading-dot"></view>
                    <view class="carepal-chat-loading-dot"></view>
                  </view>
                </view>
              </view>
            </view>

            <view class="carepal-chat-input">
              <view class="carepal-chat-input-row">
                <var-button
                  type="primary"
                  round
                  class="carepal-chat-mic"
                  color="linear-gradient(135deg, #ff7a7a 0%, #ffb347 100%)"
                  text-color="#ffffff"
                  @tap.stop="onMicModeTrigger"
                  @click.stop="onMicModeTrigger"
                >
                  {{ chatInputMode === 'text' ? '🎤' : '⌨' }}
                </var-button>
                <view v-if="chatInputMode === 'text'" class="carepal-chat-input-main">
                  <textarea
                    class="carepal-chat-textarea"
                    v-model="inputText"
                    placeholder="请输入要咨询的问题，例如：帮我看看今晚是否需要加一次药？"
                    maxlength="300"
                    :confirm-type="'send'"
                    @confirm="onSend"
                  ></textarea>
                </view>
                <view
                  v-else
                  class="carepal-chat-hold-to-talk"
                  @touchstart.stop.prevent="onVoiceHoldStart"
                  @touchend.stop.prevent="onVoiceHoldEnd"
                  @touchcancel.stop.prevent="onVoiceHoldCancel"
                  @mousedown.stop.prevent="onVoiceHoldStart"
                  @mouseup.stop.prevent="onVoiceHoldEnd"
                  @mouseleave.stop.prevent="onVoiceHoldCancel"
                >
                  {{ isRecording ? '松开发送语音' : '长按输入语音' }}
                </view>
                <var-button
                  v-if="chatInputMode === 'text'"
                  type="primary"
                  size="small"
                  class="carepal-chat-send"
                  @tap="onSend"
                >
                  发送
                </var-button>
              </view>
              <view class="carepal-chat-mic-status">{{ recordingStatusText }}</view>
            </view>

            <view v-if="copyTextPanelVisible" class="carepal-chat-copy-mask" @tap="closeCopyTextPanel">
              <view class="carepal-chat-copy-panel" @tap.stop>
                <view class="carepal-chat-copy-title">选择复制</view>
                <textarea
                  class="carepal-chat-copy-textarea"
                  :value="copyTextContent"
                  maxlength="-1"
                ></textarea>
                <view class="carepal-chat-copy-actions">
                  <var-button size="small" type="primary" @tap="copyTextContentNow">复制全文</var-button>
                  <var-button size="small" plain @tap="closeCopyTextPanel">关闭</var-button>
                </view>
              </view>
            </view>
          </view>

          <!-- 模块 2：日程表 -->
          <view v-else-if="currentModule === 'schedule'" class="carepal-panel carepal-schedule">
            <view class="carepal-panel-header">
              <view class="carepal-panel-title">今日日程表</view>
              <view class="carepal-panel-subtitle">{{ selectedCalendarDetail ? `${selectedCalendarDetail.dateText} · 用药计划` : '用药 · 训练 · 随访' }}</view>
            </view>
            <view class="carepal-table">
              <view class="carepal-table-head">
                <view class="carepal-table-col time">时间</view>
                <view class="carepal-table-col medication">用药情况</view>
                <view class="carepal-table-col bp">血压</view>
                <view class="carepal-table-col weight">体重</view>
                <view class="carepal-table-col symptom">症状</view>
                <view class="carepal-table-col mood">心情</view>
                <view class="carepal-table-col matter">事宜</view>
              </view>
              <view
                :class="[
                  'carepal-table-row',
                  activeScheduleTime === item.time ? 'is-highlight' : '',
                  activeSchedulePulse && activeScheduleTime === item.time ? 'is-pulse' : '',
                ]"
                :id="'schedule-row-' + item.time.replace(':', '')"
                v-for="item in displayedScheduleItems"
                :key="item.id"
              >
                <view class="carepal-table-col time" @tap="openScheduleFieldEditor(item, 'time')">{{ item.time }}</view>
                <view class="carepal-table-col medication" @tap="openScheduleFieldEditor(item, 'medicine')">
                  <view class="carepal-medication-name">{{ item.medicine }}</view>
                  <view
                    :class="['carepal-status-pill', 'is-clickable', 'is-' + item.medicationTagType]"
                    @tap.stop="toggleScheduleTaken(item)"
                  >
                    {{ item.medicationTag }}
                  </view>
                </view>
                <view class="carepal-table-col bp" @tap="openScheduleFieldEditor(item, 'bp')">{{ item.bp }}</view>
                <view class="carepal-table-col weight" @tap="openScheduleFieldEditor(item, 'weight')">{{ item.weight || '—' }}</view>
                <view class="carepal-table-col symptom" @tap="openScheduleFieldEditor(item, 'symptom')">{{ item.symptom || '—' }}</view>
                <view class="carepal-table-col mood" @tap="openScheduleFieldEditor(item, 'mood')">{{ item.mood || '—' }}</view>
                <view class="carepal-table-col matter" @tap="openScheduleFieldEditor(item, 'matter')">
                  <view class="carepal-matter-text">{{ item.matter }}</view>
                  <view :class="['carepal-status-pill', 'is-mini', 'is-' + item.matterTagType]">{{ item.matterTag }}</view>
                </view>
              </view>
            </view>

            <view class="carepal-calendar-card">
              <view class="carepal-calendar-header">
                <view class="carepal-calendar-title">服药月历表</view>
                <view class="carepal-calendar-controls">
                  <var-button size="mini" plain class="carepal-calendar-btn" @tap="goPrevMonth">上月</var-button>
                  <var-button size="mini" class="carepal-calendar-btn" @tap="goCurrentMonth">当月</var-button>
                </view>
              </view>
              <view class="carepal-calendar-subtitle">{{ calendarMonthLabel }}</view>

              <view class="carepal-calendar-year-head">
                <var-button size="mini" plain class="carepal-calendar-btn" @tap="goPrevYear">上一年</var-button>
                <view class="carepal-calendar-year-title">{{ currentCalendarYear }} 年月历记录</view>
                <var-button size="mini" plain class="carepal-calendar-btn" @tap="goNextYear">下一年</var-button>
              </view>
              <view class="carepal-calendar-year-grid">
                <view
                  v-for="month in calendarYearOverview"
                  :key="month.monthIndex"
                  :class="[
                    'carepal-calendar-year-item',
                    month.monthIndex === currentCalendarMonth ? 'is-active' : '',
                    month.completion >= 0.8 ? 'is-good' : 'is-warn',
                  ]"
                  @tap="selectCalendarMonth(month.monthIndex)"
                >
                  <view class="carepal-calendar-year-item-title">{{ month.label }}</view>
                  <view class="carepal-calendar-year-item-meta">{{ month.isFutureMonth ? `-/${month.totalDays} 天正常` : `${month.takenDays}/${month.totalDays} 天正常` }}</view>
                  <view class="carepal-calendar-year-progress">
                    <view class="carepal-calendar-year-progress-fill" :style="{ width: month.isFutureMonth ? '0%' : `${Math.round(month.completion * 100)}%` }"></view>
                  </view>
                  <view class="carepal-calendar-year-item-rate">{{ month.isFutureMonth ? '未记录' : `完成率 ${Math.round(month.completion * 100)}%` }}</view>
                </view>
              </view>
              <view class="carepal-calendar-inline-tip">点击月份卡，在右侧查看该月日历</view>
              <view
                :class="['carepal-calendar-drawer', calendarDrawerVisible ? 'is-open' : '']"
                @tap.stop
              >
                <view class="carepal-calendar-drawer-header">
                  <view class="carepal-calendar-title">服药日历表 · {{ calendarMonthLabel }}</view>
                  <view class="carepal-calendar-controls">
                    <var-button size="mini" plain class="carepal-calendar-btn" @tap="goPrevMonth">上月</var-button>
                    <var-button size="mini" class="carepal-calendar-btn" @tap="goCurrentMonth">当月</var-button>
                    <var-button size="mini" plain class="carepal-calendar-btn" @tap="closeCalendarDrawer">关闭</var-button>
                  </view>
                </view>
  
                <view class="carepal-calendar-weekdays">
                  <view
                    v-for="weekday in calendarWeekdays"
                    :key="weekday"
                    class="carepal-calendar-weekday"
                  >
                    {{ weekday }}
                  </view>
                </view>
                <view class="carepal-calendar-grid">
                  <view
                    v-for="(cell, idx) in medicationCalendarCells"
                    :key="idx"
                    :class="[
                      'carepal-calendar-cell',
                      cell.day ? '' : 'is-empty',
                      cell.day && cell.isUnrecorded ? 'is-unrecorded' : '',
                      cell.day && !cell.isUnrecorded && cell.taken ? 'is-ok' : '',
                      cell.day && !cell.isUnrecorded && !cell.taken ? 'is-miss' : '',
                      cell.day && selectedCalendarDay === cell.day ? 'is-selected' : '',
                      cell.day && isCalendarCellBeforeToday(cell.day) ? 'is-before-today' : '',
                      cell.day && isCalendarCellAfterToday(cell.day) ? 'is-after-today' : '',
                    ]"
                    @tap="onCalendarDayTap(cell)"
                  >
                    <template v-if="cell.day">
                      <view class="carepal-calendar-day">{{ cell.day }}</view>
                      <view v-if="cell.isUnrecorded" class="carepal-calendar-day-note">未记录</view>
                    </template>
                  </view>
                </view>
              </view>
            </view>

            <view v-if="scheduleEditDialogVisible" class="carepal-schedule-edit-mask" @tap="closeScheduleFieldEditor">
              <view class="carepal-schedule-edit-panel" @tap.stop>
                <view class="carepal-schedule-edit-title">编辑 {{ scheduleEditLabel }}</view>
                <view class="carepal-schedule-edit-subtitle">时间：{{ scheduleEditTime }}</view>
                <input
                  v-model="scheduleEditValue"
                  class="carepal-schedule-edit-input"
                  :placeholder="`请输入${scheduleEditLabel}`"
                />
                <view class="carepal-schedule-edit-actions">
                  <var-button size="small" plain @tap="closeScheduleFieldEditor">取消</var-button>
                  <var-button size="small" type="primary" @tap="confirmScheduleFieldEdit">保存</var-button>
                </view>
              </view>
            </view>
          </view>

          <!-- 模块 3：OCR 上传 -->
          <view v-else-if="currentModule === 'ocr'" class="carepal-panel carepal-ocr">
            <view class="carepal-panel-header">
              <view class="carepal-panel-title">药盒 / 处方 OCR 识别</view>
              <view class="carepal-panel-subtitle">上传或拍摄药盒图片，自动识别药品与用药信息</view>
            </view>
            <view :class="['carepal-ocr-layout', ocrInputMode === 'camera' && ocrCameraVisible ? 'is-camera-live' : '']">
              <view class="carepal-ocr-left">
                <view class="carepal-ocr-actions">
                  <var-button :type="ocrInputMode === 'album' ? 'primary' : 'default'" class="carepal-ocr-btn" @tap="setOcrInputMode('album')">上传照片</var-button>
                  <var-button :type="ocrInputMode === 'camera' ? 'primary' : 'default'" class="carepal-ocr-btn" @tap="setOcrInputMode('camera')">拍照识别</var-button>
                </view>

                <view class="carepal-ocr-drop" @tap="onOcrDropTap">
                  <view class="carepal-ocr-drop-inner carepal-ocr-drop-inner--camera" v-if="ocrInputMode === 'camera' && ocrCameraVisible">
                    <video
                      ref="ocrCameraVideo"
                      class="carepal-camera-video"
                      autoplay
                      playsinline
                      muted
                    ></video>
                    <view class="carepal-ocr-camera-actions">
                      <var-button plain class="carepal-camera-btn" @tap.stop="closeOcrCamera">取消</var-button>
                      <var-button type="primary" class="carepal-camera-btn" @tap.stop="captureOcrPhoto">拍照</var-button>
                    </view>
                  </view>
                  <view class="carepal-ocr-drop-inner" v-else-if="ocrImageUrl">
                    <image class="carepal-ocr-preview" :src="ocrImageUrl" mode="aspectFit" />
                    <view class="carepal-ocr-preview-hint">点击更换图片</view>
                  </view>
                  <view class="carepal-ocr-drop-inner" v-else>
                    <view class="carepal-ocr-icon">📷</view>
                    <view class="carepal-ocr-text">{{ ocrInputMode === 'camera' ? '点击拍照识别以打开摄像头' : '点击选择图片进行识别' }}</view>
                    <view class="carepal-ocr-hint">支持 jpg、png 等常见格式，建议确保文字清晰可见</view>
                    <view class="carepal-ocr-steps">
                      <view class="carepal-ocr-step"><text class="carepal-ocr-step-index">1</text> 上传药盒或处方图片</view>
                      <view class="carepal-ocr-step"><text class="carepal-ocr-step-index">2</text> 系统识别关键信息</view>
                      <view class="carepal-ocr-step"><text class="carepal-ocr-step-index">3</text> 右侧生成 AI 用药解读</view>
                    </view>
                  </view>
                </view>

                <view class="carepal-ocr-submit-row">
                  <var-button
                    type="primary"
                    class="carepal-ocr-submit-btn"
                    :disabled="!ocrImageUrl || ocrSubmitting"
                    :loading="ocrSubmitting"
                    @tap="submitOcrAnalyze(false)"
                  >开始识别</var-button>
                  <var-button
                    plain
                    class="carepal-ocr-submit-btn"
                    :disabled="!ocrImageUrl || ocrSubmitting"
                    @tap="submitOcrAnalyze(true)"
                  >识别并朗读</var-button>
                </view>
              </view>

              <view class="carepal-ocr-right">
                <view class="carepal-ocr-explain">
                  <view class="carepal-ocr-explain-title">AI 解读</view>
                  <view class="carepal-ocr-explain-subtitle">识别结果、用药要点与注意事项将在此显示</view>
                  <view class="carepal-ocr-explain-body">
                    <view v-if="ocrExplainText" class="carepal-ocr-explain-text">{{ ocrExplainText }}</view>
                    <view v-else class="carepal-ocr-explain-placeholder">
                      {{ ocrImageUrl ? '已选择图片，点击“开始识别”上传到后端' : '请先在左侧上传图片' }}
                    </view>
                  </view>
                </view>
              </view>
            </view>
          </view>

          <!-- 模块 4：周报告 -->
          <view v-else-if="currentModule === 'weekly-report'" class="carepal-panel carepal-weekly">
            <view class="carepal-panel-header">
              <view class="carepal-panel-title">周报告</view>
              <view class="carepal-panel-subtitle">统一问卷工作台，提交后由 AI 生成周报告</view>
            </view>

            <view class="carepal-weekly-card carepal-weekly-card--hero">
              <view class="carepal-weekly-section-title">本周问卷（统一入口）</view>
              <view class="carepal-weekly-hint">周区间自动选择：{{ currentWeekRange }}</view>
              <view class="carepal-weekly-hint">填写完成后将提交给 AI 生成正式周报告。</view>
            </view>

            <view class="carepal-weekly-card">
              <view class="carepal-weekly-section-title">手动问卷填写</view>
              <view class="carepal-weekly-score-legend">
                <view class="carepal-weekly-label">分数解释</view>
                <view class="carepal-weekly-legend-row"><text class="carepal-weekly-legend-dot is-0"></text>0分：正常/无明显影响</view>
                <view class="carepal-weekly-legend-row"><text class="carepal-weekly-legend-dot is-1"></text>1分：轻微，基本不影响日常</view>
                <view class="carepal-weekly-legend-row"><text class="carepal-weekly-legend-dot is-2"></text>2分：轻度，出现一定困扰</view>
                <view class="carepal-weekly-legend-row"><text class="carepal-weekly-legend-dot is-3"></text>3分：中度，影响较明显</view>
                <view class="carepal-weekly-legend-row"><text class="carepal-weekly-legend-dot is-4"></text>4分：重度，严重影响生活</view>
              </view>

              <view class="carepal-weekly-page-tabs">
                <var-button
                  v-for="(page, pageIndex) in weeklyQuestionnairePages"
                  :key="'weekly-page-tab-' + pageIndex"
                  size="small"
                  :class="['carepal-weekly-page-tab-btn', activeWeeklyPageIndex === pageIndex ? 'is-active' : '']"
                  :type="activeWeeklyPageIndex === pageIndex ? 'primary' : 'default'"
                  :color="
                    activeWeeklyPageIndex === pageIndex
                      ? (darkMode
                        ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.44) 0%, rgba(147, 197, 253, 0.4) 55%, rgba(186, 230, 253, 0.38) 100%)'
                        : 'linear-gradient(135deg, #9bcfff 0%, #b3dcff 56%, #cdf0ff 100%)')
                      : (darkMode
                        ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.16) 0%, rgba(186, 230, 253, 0.14) 100%)'
                        : 'linear-gradient(135deg, #f4faff 0%, #ecf6ff 100%)')
                  "
                  :text-color="activeWeeklyPageIndex === pageIndex ? (darkMode ? '#f3fbff' : '#154672') : (darkMode ? '#dce8fa' : '#4a6689')"
                  @tap="switchWeeklyPage(pageIndex)"
                >
                  {{ page.title }}
                </var-button>
              </view>

              <view class="carepal-weekly-page-head">
                <view class="carepal-weekly-page-title">{{ currentWeeklyPage.title }}</view>
                <view class="carepal-weekly-page-index">第 {{ activeWeeklyPageIndex + 1 }} / {{ weeklyQuestionnairePages.length }} 页</view>
              </view>

              <transition name="carepal-weekly-page-fade" mode="out-in">
                <view class="carepal-weekly-score-list" :key="'weekly-page-' + activeWeeklyPageIndex">
                  <view class="carepal-weekly-score-item" v-for="question in currentWeeklyQuestions" :key="'manual-q-' + question.id">
                    <view class="carepal-weekly-score-title">{{ question.code }} {{ question.title }}</view>
                    <view class="carepal-weekly-score-prompt">{{ question.prompt }}</view>
                    <view class="carepal-weekly-score-options">
                      <var-button
                        v-for="option in question.options"
                        :key="'q' + question.id + '-opt-' + option.score"
                        size="mini"
                        :class="['carepal-weekly-score-btn', weeklyManualForm.scores[question.id] === option.score ? 'is-active' : '']"
                        :type="weeklyManualForm.scores[question.id] === option.score ? 'primary' : 'default'"
                        :color="
                          weeklyManualForm.scores[question.id] === option.score
                            ? (darkMode
                              ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.46) 0%, rgba(147, 197, 253, 0.42) 50%, rgba(186, 230, 253, 0.4) 100%)'
                              : 'linear-gradient(135deg, #93c9ff 0%, #aedaff 52%, #caf0ff 100%)')
                            : (darkMode
                              ? 'linear-gradient(135deg, rgba(125, 211, 252, 0.14) 0%, rgba(186, 230, 253, 0.12) 100%)'
                              : 'linear-gradient(135deg, #f6fbff 0%, #edf7ff 100%)')
                        "
                        :text-color="weeklyManualForm.scores[question.id] === option.score ? (darkMode ? '#f4fbff' : '#14406b') : (darkMode ? '#dbe8fa' : '#4f6f95')"
                        @tap="setWeeklyManualScore(question.id, option.score)"
                      >
                        {{ option.score }}分
                      </var-button>
                    </view>
                    <view class="carepal-weekly-score-desc" v-if="weeklyManualForm.scores[question.id] !== null">
                      当前：{{ question.options[weeklyManualForm.scores[question.id]].label }}
                    </view>
                  </view>
                </view>
              </transition>

              <view class="carepal-weekly-page-actions">
                <var-button
                  size="small"
                  plain
                  class="carepal-weekly-page-action-btn"
                  :disabled="activeWeeklyPageIndex === 0"
                  @tap="goPrevWeeklyPage"
                >上一页</var-button>
                <var-button
                  size="small"
                  plain
                  class="carepal-weekly-page-action-btn"
                  :disabled="activeWeeklyPageIndex >= weeklyQuestionnairePages.length - 1"
                  @tap="goNextWeeklyPage"
                >下一页</var-button>
              </view>

              <view class="carepal-weekly-form-item">
                <view class="carepal-weekly-label">补充说明</view>
                <textarea
                  v-model="weeklyManualForm.note"
                  class="carepal-weekly-textarea"
                  placeholder="可填写本周异常事件、情绪波动、需要医生关注的问题"
                  maxlength="1000"
                ></textarea>
              </view>
              <var-button type="primary" class="carepal-weekly-submit" @tap="submitWeeklyQuestionnaireToAi">提交问卷，交由 AI 生成周报告</var-button>
              <view class="carepal-weekly-file-name" v-if="weeklyAiSubmitHint">{{ weeklyAiSubmitHint }}</view>
            </view>

            <view class="carepal-weekly-result" v-if="weeklyReportText || weeklyReportEncouragement">
              <view class="carepal-weekly-section-title">AI 周报建议</view>
              <view class="carepal-weekly-result-text" v-if="weeklyReportText">{{ weeklyReportText }}</view>
              <view class="carepal-weekly-result-encouragement" v-if="weeklyReportEncouragement">{{ weeklyReportEncouragement }}</view>
            </view>
          </view>

          <!-- 模块 5：监控 -->
          <view v-else-if="currentModule === 'monitor'" class="carepal-panel carepal-monitor">
            <view class="carepal-panel-header">
              <view class="carepal-panel-title">监控</view>
              <view class="carepal-panel-subtitle">跌倒风险检测（后续接入 YOLO 跌倒检测接口）</view>
            </view>

            <view class="carepal-monitor-layout">
              <view class="carepal-monitor-left">
                <view class="carepal-monitor-card">
                  <view class="carepal-monitor-card-title">检测控制</view>
                  <view class="carepal-monitor-actions">
                    <var-button type="primary" class="carepal-monitor-btn" @tap="toggleMonitorCamera">
                      {{ monitorCameraVisible ? '关闭摄像头' : '打开摄像头' }}
                    </var-button>
                    <var-button
                      class="carepal-monitor-btn"
                      :type="monitorDetecting ? 'danger' : 'default'"
                      :disabled="!monitorCameraVisible"
                      @tap="toggleMonitorDetecting"
                    >
                      {{ monitorDetecting ? '停止检测' : '开始检测' }}
                    </var-button>
                  </view>

                  <view class="carepal-monitor-status-row">
                    <view class="carepal-monitor-status-label">当前状态</view>
                    <view :class="['carepal-monitor-status-pill', monitorDetecting ? 'is-running' : 'is-idle']">
                      {{ monitorDetecting ? '检测中' : '未检测' }}
                    </view>
                  </view>
                  <view class="carepal-monitor-status-row">
                    <view class="carepal-monitor-status-label">检测结果</view>
                    <view :class="['carepal-monitor-status-pill', monitorLastResult.hasFall ? 'is-alert' : 'is-safe']">
                      {{ monitorLastResult.hasFall ? '疑似跌倒' : '未发现跌倒' }}
                    </view>
                  </view>
                  <view class="carepal-monitor-hint">{{ monitorStatusHint }}</view>
                </view>
              </view>

              <view class="carepal-monitor-right">
                <view class="carepal-monitor-view" style="position: relative;">
                  <video
                    v-if="monitorCameraVisible"
                    ref="monitorCameraVideo"
                    class="carepal-monitor-video"
                    autoplay
                    playsinline
                    muted
                  ></video>
                  <canvas 
                    v-if="monitorCameraVisible" 
                    canvas-id="yoloCanvas" 
                    id="yoloCanvas"
                    class="carepal-monitor-canvas"
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"
                  ></canvas>
                  <view v-else class="carepal-monitor-placeholder">
                    <view class="carepal-monitor-placeholder-title">监控画面</view>
                    <view class="carepal-monitor-placeholder-text">点击左侧“打开摄像头”开始预览</view>
                  </view>
                </view>
              </view>
            </view>
          </view>

          <!-- 模块 6：我的 / 设置 -->
          <view v-else class="carepal-panel carepal-profile">
            <view class="carepal-panel-header">
              <view class="carepal-panel-title">我们</view>
            </view>

            <view class="carepal-profile-section">
              <view class="carepal-profile-title">账户设置</view>

              <view class="carepal-profile-row carepal-profile-row--avatar">
                <view class="carepal-profile-label">头像</view>
                <view class="carepal-profile-control carepal-profile-control--avatar">
                  <image
                    class="carepal-profile-avatar"
                    :src="profile.avatar || '/static/icons/profile.svg'"
                    mode="aspectFill"
                  />
                  <var-button size="small" class="carepal-profile-btn" @tap="onPickAvatar">更换</var-button>
                </view>
              </view>

              <view class="carepal-profile-row carepal-profile-row--form">
                <view class="carepal-profile-label">名字</view>
                <view class="carepal-profile-control carepal-profile-control--edit" @tap.stop>
                    <template v-if="editField === 'name'">
                    <var-input v-model="editValue" placeholder="请输入名字" />
                    <var-button size="small" class="carepal-profile-btn" @tap="applyEdit">保存</var-button>
                    <var-button size="small" plain class="carepal-profile-btn" @tap="cancelEdit">取消</var-button>
                  </template>
                  <template v-else>
                    <view class="carepal-profile-value carepal-profile-value--click" @tap="beginEdit('name')">
                      {{ profile.name || '未设置' }}
                    </view>
                  </template>
                </view>
              </view>

              <view class="carepal-profile-row carepal-profile-row--form">
                <view class="carepal-profile-label">绑定手机号</view>
                <view class="carepal-profile-control carepal-profile-control--edit" @tap.stop>
                  <template v-if="editField === 'phone'">
                    <var-input v-model="editValue" type="number" maxlength="11" placeholder="请输入手机号" />
                    <var-button size="small" class="carepal-profile-btn" @tap="applyEdit">保存</var-button>
                    <var-button size="small" plain class="carepal-profile-btn" @tap="cancelEdit">取消</var-button>
                  </template>
                  <template v-else>
                    <view class="carepal-profile-value carepal-profile-value--click" @tap="beginEdit('phone')">
                      {{ profile.phone || '未绑定' }}
                    </view>
                  </template>
                </view>
              </view>

              <view class="carepal-profile-row carepal-profile-row--form">
                <view class="carepal-profile-label">紧急联系人</view>
                <view class="carepal-profile-control carepal-profile-control--edit" @tap.stop>
                  <template v-if="editField === 'emergencyName'">
                    <var-input v-model="editValue" placeholder="请输入紧急联系人姓名" />
                    <var-button size="small" class="carepal-profile-btn" @tap="applyEdit">保存</var-button>
                    <var-button size="small" plain class="carepal-profile-btn" @tap="cancelEdit">取消</var-button>
                  </template>
                  <template v-else>
                    <view class="carepal-profile-value carepal-profile-value--click" @tap="beginEdit('emergencyName')">
                      {{ profile.emergencyName || '未设置' }}
                    </view>
                  </template>
                </view>
              </view>

              <view class="carepal-profile-row carepal-profile-row--form">
                <view class="carepal-profile-label">紧急联系人邮箱</view>
                <view class="carepal-profile-control carepal-profile-control--edit" @tap.stop>
                  <template v-if="editField === 'emergencyEmail'">
                    <var-input v-model="editValue" maxlength="80" placeholder="请输入紧急联系人邮箱" />
                    <var-button size="small" class="carepal-profile-btn" @tap="applyEdit">保存</var-button>
                    <var-button size="small" plain class="carepal-profile-btn" @tap="cancelEdit">取消</var-button>
                  </template>
                  <template v-else>
                    <view class="carepal-profile-value carepal-profile-value--click" @tap="beginEdit('emergencyEmail')">
                      {{ profile.emergencyEmail || '未设置' }}
                    </view>
                  </template>
                </view>
              </view>

              <view class="carepal-profile-actions">
                <var-button type="primary" class="carepal-profile-save" @tap="onSaveProfile">保存修改</var-button>
              </view>
            </view>

            <view class="carepal-profile-section carepal-profile-section--basic">
              <view class="carepal-profile-title">基础设置</view>
              <view class="carepal-profile-row">
                <view class="carepal-profile-label">长辈关怀模式</view>
                <view class="carepal-profile-control">
                  <var-switch v-model="elderMode" />
                </view>
              </view>
              <view class="carepal-profile-row">
                <view class="carepal-profile-label">暗夜模式</view>
                <view class="carepal-profile-control">
                  <var-switch v-model="darkMode" />
                </view>
              </view>
            </view>
          </view>
            </view>
          </transition>
        </view>
      </view>
    </view>

    <view v-if="loginDialogVisible" class="carepal-login-mask" @tap="closeLoginDialog">
      <view class="carepal-login-panel" @tap.stop>
        <view class="carepal-login-tabs">
          <var-button
            size="small"
            :type="authMode === 'login' ? 'primary' : 'default'"
            class="carepal-login-tab-btn"
            @tap="switchAuthMode('login')"
          >
            登录
          </var-button>
          <var-button
            size="small"
            :type="authMode === 'register' ? 'primary' : 'default'"
            class="carepal-login-tab-btn"
            @tap="switchAuthMode('register')"
          >
            注册
          </var-button>
        </view>
        <view class="carepal-login-title">{{ authMode === 'login' ? '账号登录' : '创建账号' }}</view>
        <view class="carepal-login-subtitle">{{ authMode === 'login' ? '登录后可调用受保护接口' : '注册成功后将自动登录' }}</view>
        <var-input v-model="loginForm.username" :maxlength="authRules.usernameMaxLength" placeholder="请输入用户名" class="carepal-login-input" />
        <var-input v-model="loginForm.password" type="password" :maxlength="authRules.passwordMaxLength" :placeholder="`请输入密码（至少 ${authRules.passwordMinLength} 位）`" class="carepal-login-input" />
        <template v-if="authMode === 'register'">
          <var-input
            v-model="loginForm.emergencyName"
            placeholder="请输入紧急联系人"
            class="carepal-login-input"
          />
          <var-input
            v-model="loginForm.emergencyEmail"
            maxlength="80"
            placeholder="请输入紧急联系人邮箱"
            class="carepal-login-input"
          />
        </template>
        <view class="carepal-login-actions">
          <var-button
            v-if="isUserLoggedIn"
            plain
            class="carepal-login-btn carepal-login-btn--danger"
            @tap="logout"
          >
            退出登录
          </var-button>
          <var-button plain class="carepal-login-btn" @tap="closeLoginDialog">取消</var-button>
          <var-button type="primary" class="carepal-login-btn" :loading="authSubmitting" @tap="submitAuth">
            {{ authMode === 'login' ? '登录' : '注册' }}
          </var-button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { APP_CONFIG } from '../../config/app.config'

const WEEKLY_NON_MOTOR_QUESTIONS = [
  {
    id: 'q1',
    code: '1.',
    title: '睡眠问题',
    prompt: '在过去一周内，您是否有晚上入睡困难或是整夜无法入睡的情况？',
    options: [
      { score: 0, label: '正常：没有睡眠问题。' },
      { score: 1, label: '轻微：有睡眠问题，但通常不会造成整夜入眠上的困难。' },
      { score: 2, label: '轻度：有睡眠问题，通常会造成整夜入眠上一些困难。' },
      { score: 3, label: '中度：有睡眠问题，会造成整夜睡眠上很大的困难，但一半以上时间仍可入睡。' },
      { score: 4, label: '重度：整夜大部分时间无法入睡。' },
    ],
  },
  {
    id: 'q2',
    code: '2.',
    title: '白天嗜睡',
    prompt: '在过去一周内，您是否有白天维持清醒状态的困难？',
    options: [
      { score: 0, label: '没有：没有白天嗜睡情形。' },
      { score: 1, label: '轻微：会有白天嗜睡，但可以忍住并保持清醒。' },
      { score: 2, label: '轻度：独处或放松时有时会睡着，例如阅读或看电视。' },
      { score: 3, label: '中度：不该睡着时有时会睡着，例如吃东西或交谈时。' },
      { score: 4, label: '重度：不该睡着时经常会睡着。' },
    ],
  },
  {
    id: 'q3',
    code: '3.',
    title: '疼痛和其它感觉',
    prompt: '在过去一周内，身体是否有疼痛、刺痛或抽痛等不舒服感觉？',
    options: [
      { score: 0, label: '正常：没有不舒服的感觉。' },
      { score: 1, label: '轻微：有这些感觉，但仍可毫无困难地做事并与人相处。' },
      { score: 2, label: '轻度：做事或与人相处时会造成一些困扰。' },
      { score: 3, label: '中度：造成很大困扰，但不会让我无法工作或与人相处。' },
      { score: 4, label: '重度：会让我无法工作或与人相处。' },
    ],
  },
  {
    id: 'q4',
    code: '4.',
    title: '排尿问题',
    prompt: '在过去一周内，您是否有控制排尿的困难，例如急尿、频尿或漏尿？',
    options: [
      { score: 0, label: '没有：没有控制排尿的问题。' },
      { score: 1, label: '轻微：频尿但不影响日常活动。' },
      { score: 2, label: '轻度：造成日常活动一些困难，但不会漏尿。' },
      { score: 3, label: '中度：造成很大困难，且会漏尿。' },
      { score: 4, label: '重度：无法控制排尿，需使用尿布、看护垫或导尿管。' },
    ],
  },
  {
    id: 'q5',
    code: '5.',
    title: '便秘问题',
    prompt: '在过去一周内，您是否有便秘问题，造成肠胃蠕动困难？',
    options: [
      { score: 0, label: '正常：没有便秘问题。' },
      { score: 1, label: '轻微：需要额外努力排便，但不干扰活动或造成不适。' },
      { score: 2, label: '轻度：做事时会有一些困扰或不适。' },
      { score: 3, label: '中度：会有很大困扰或不适，但不会让我无法做事。' },
      { score: 4, label: '重度：经常需要他人身体外在协助才能顺利排便。' },
    ],
  },
  {
    id: 'q6',
    code: '6.',
    title: '站起时头晕',
    prompt: '在过去一周内，坐着/躺着后站起时是否有头昏、晕眩或昏沉感？',
    options: [
      { score: 0, label: '正常：无晕眩或头昏眼花。' },
      { score: 1, label: '轻微：有过晕眩或头昏眼花，但不影响做事。' },
      { score: 2, label: '轻度：需要扶着东西，但不需坐下或躺回去。' },
      { score: 3, label: '中度：需要坐下或躺下，避免昏倒或跌倒。' },
      { score: 4, label: '重度：会造成昏倒或跌倒。' },
    ],
  },
  {
    id: 'q7',
    code: '7.',
    title: '疲劳感',
    prompt: '在过去一周内，您是否经常觉得疲倦（不包含想睡或悲伤）？',
    options: [
      { score: 0, label: '正常：没有疲倦感。' },
      { score: 1, label: '轻微：有疲倦感，但不影响做事与社交。' },
      { score: 2, label: '轻度：会造成做事及与人相处上的一些困难。' },
      { score: 3, label: '中度：会造成很大困难，但不会让我无法做任何事情。' },
      { score: 4, label: '重度：会让我无法做事或与人相处。' },
    ],
  },
]

const WEEKLY_MOTOR_QUESTIONS = [
  {
    id: 'q2_1',
    code: '2.1',
    title: '言语',
    prompt: '过去一周内，您有言语上的问题吗？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我说话轻声、含糊不清或不顺畅，但不需要重复述说。' },
      { score: 2, label: '轻度：我偶尔需要重复述说一遍，但不是每天都这样。' },
      { score: 3, label: '中度：我因说话不够清楚，因此每天别人都要我重复述说，虽然他们可以了解我的意思。' },
      { score: 4, label: '重度：我的语言能力大部分时间或几乎完全无法被了解。' },
    ],
  },
  {
    id: 'q2_2',
    code: '2.2',
    title: '唾液分泌与流口水',
    prompt: '过去一周内，当清醒或睡觉时，您通常有唾液过多的问题吗？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我有过多的唾液在口中，但不会流口水。' },
      { score: 2, label: '轻度：我睡觉时会流一些口水，但清醒时并不会。' },
      { score: 3, label: '中度：我清醒时会流一些口水，但通常不需要面纸或手帕擦拭。' },
      { score: 4, label: '重度：我会流很多口水，一直需要面纸或手帕擦拭，避免沾湿衣服。' },
    ],
  },
  {
    id: 'q2_3',
    code: '2.3',
    title: '咀嚼与吞咽',
    prompt: '过去一周内，您通常有吞药或吃饭的问题吗？是否需要将药丸切碎或磨碎，或将食物制成软质、切碎、温和饮食，以避免被呛到？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我觉得咀嚼变慢或吞咽须特别费力，但不会呛到或须准备特殊饮食。' },
      { score: 2, label: '轻度：我因有咀嚼或吞咽问题，需要将药丸切碎或准备特殊饮食，但过去一周内没有呛到情形发生。' },
      { score: 3, label: '中度：过去一周内，我至少呛到一次。' },
      { score: 4, label: '重度：我因为咀嚼与吞咽困难，需插喂食管。' },
    ],
  },
  {
    id: 'q2_4',
    code: '2.4',
    title: '进食能力',
    prompt: '过去一周内，您在进食或是使用餐具上是否有困难呢？如：以手指拿食物或使用刀叉、汤匙、筷子等食器上是否有困难？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我会缓慢，但不需要帮忙，且进餐时不会使食物掉落出来。' },
      { score: 2, label: '轻度：我进餐时会缓慢，偶尔会使食物掉（散落）出来；有时需要别人的帮助，例如夹菜。' },
      { score: 3, label: '中度：我进餐时需要别人更多的帮助，但有些事可以独自做。' },
      { score: 4, label: '重度：我进餐时大部分或所有的需要别人的帮助。' },
    ],
  },
  {
    id: 'q2_5',
    code: '2.5',
    title: '穿衣',
    prompt: '过去一周内，您穿衣是否通常有困难？例如：动作缓慢或需要帮忙扣扣子、拉拉链、或穿脱衣服、或首饰吗？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我动作缓慢，但不需要帮忙。' },
      { score: 2, label: '轻度：我动作缓慢，有时需要别人的帮助，例如扣扣子、戴手镯。' },
      { score: 3, label: '中度：我穿衣时需要别人很多的帮助。' },
      { score: 4, label: '重度：我穿衣时大部分或完全地需要别人的帮助。' },
    ],
  },
  {
    id: 'q2_6',
    code: '2.6',
    title: '卫生清洁',
    prompt: '过去一周内，您在洗澡、沐浴、刮胡子、刷牙、梳头发、或其它个人卫生清洁上，是否通常有动作缓慢或需要帮忙？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我有点缓慢，但不需要帮忙。' },
      { score: 2, label: '轻度：我在一些卫生清洁方面需要别人的帮助。' },
      { score: 3, label: '中度：我很多卫生清洁方面需要别人的帮助。' },
      { score: 4, label: '重度：我所有卫生清洁大部分或所有的需要别人的帮助。' },
    ],
  },
  {
    id: 'q2_7',
    code: '2.7',
    title: '写字',
    prompt: '过去一周内，您的字迹别人是否常感到难以辨识？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我写字有点缓慢、笨拙、不工整，但可以辨认所有字体。' },
      { score: 2, label: '轻度：我某些字不清楚且难以辨认。' },
      { score: 3, label: '中度：我许多字不清楚且难以辨认。' },
      { score: 4, label: '重度：我大部分或所有的字体无法辨认。' },
    ],
  },
  {
    id: 'q2_8',
    code: '2.8',
    title: '嗜好和其它活动',
    prompt: '过去一周内，您从事嗜好或其它活动时是否有遭到困难？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我动作有点缓慢，但能轻易地从事活动。' },
      { score: 2, label: '轻度：我从事活动时感到一些困难。' },
      { score: 3, label: '中度：我从事活动时感到很大的困难，但大部分活动都还可以去做。' },
      { score: 4, label: '重度：我无法去从事大部分或所有的活动。' },
    ],
  },
  {
    id: 'q2_9',
    code: '2.9',
    title: '翻身',
    prompt: '过去一周内，床上翻身是否经常感到困难？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我感到在床上翻身有点困难，但不需要帮忙。' },
      { score: 2, label: '轻度：我感到在床上翻身困难，且偶尔需要别人的帮助。' },
      { score: 3, label: '中度：我常常需要别人的帮助。' },
      { score: 4, label: '重度：如果没有别人的帮助，我完全没办法翻身。' },
    ],
  },
  {
    id: 'q2_10',
    code: '2.10',
    title: '震颤',
    prompt: '过去一周内，您是否经常抖动或摇摆？',
    options: [
      { score: 0, label: '正常：没有震颤。' },
      { score: 1, label: '轻微：我有抖动或震颤，但不影响日常活动。' },
      { score: 2, label: '轻度：我有抖动或震颤，且影响部分日常活动。' },
      { score: 3, label: '中度：我有抖动或震颤，且影响许多日常活动。' },
      { score: 4, label: '重度：我有抖动或震颤，且影响大多数或所有的日常活动。' },
    ],
  },
  {
    id: 'q2_11',
    code: '2.11',
    title: '起床、离开车或从较低的椅子起身',
    prompt: '过去一周内，您在起床、离开车或从较低的椅子起身是否经常感到困难？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我动作有点缓慢或笨拙，但通常一次就可以完成。' },
      { score: 2, label: '轻度：我需要尝试多次即可以完成。' },
      { score: 3, label: '中度：我有时需要别人的帮助，但多数可自己完成。' },
      { score: 4, label: '重度：我大部分或完全地需要别人的帮助。' },
    ],
  },
  {
    id: 'q2_12',
    code: '2.12',
    title: '走路与平衡',
    prompt: '过去一周内，您走路与平衡经常有困难吗？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我走路有点慢或拖着腿，但不曾使用助行器。' },
      { score: 2, label: '轻度：我偶尔使用助行器，但不需要别人的帮助。' },
      { score: 3, label: '中度：我经常使用助行器（拐杖、助步车）协助走路避免跌倒，但通常不需要别人的协助。' },
      { score: 4, label: '重度：我经常需要别人协助走路避免跌倒。' },
    ],
  },
  {
    id: 'q2_13',
    code: '2.13',
    title: '冻结',
    prompt: '过去一周内，您平日走路时，是否会突然停止或冻结，腿像粘在地板上？',
    options: [
      { score: 0, label: '正常：没有问题。' },
      { score: 1, label: '轻微：我会短暂冻结，但很容易再次起步，且不需要别人的帮助或助行器（拐杖、助步车）。' },
      { score: 2, label: '轻度：我会冻结，且再次起步时会感到困难，但不需要别人的帮助或助行器（拐杖助步车）。' },
      { score: 3, label: '中度：当我冻结时，会有很多的困难再次起步，且有时需要助行器或别人的帮助。' },
      { score: 4, label: '重度：因为冻结，大部分或全部的时间里，需要助行器或别人的帮助。' },
    ],
  },
]

const buildWeeklyQuestionnairePages = () => [
  {
    key: 'non-motor',
    title: '日常生活非运动症状体验',
    questions: WEEKLY_NON_MOTOR_QUESTIONS,
  },
  {
    key: 'motor',
    title: '日常生活运动症状体验',
    questions: WEEKLY_MOTOR_QUESTIONS,
  },
]

const buildWeeklyScoreMap = () => {
  const pages = buildWeeklyQuestionnairePages()
  const map = {}
  pages.forEach((page) => {
    page.questions.forEach((question) => {
      map[question.id] = null
    })
  })
  return map
}

export default {
  data() {
    return {
      medicationStatus: '下一次用药在 14:30',
      trainingStatus: '今日训练未开始',
      moodStatus: '等待记录',
      modules: [
        { key: 'chat', label: '对话', desc: '与 AI 对话，解读用药与康复', icon: '/static/icons/chat.svg' },
        { key: 'schedule', label: '日程表', desc: '查看今日用药与训练安排', icon: '/static/icons/schedule.svg' },
        { key: 'weekly-report', label: '周报告', desc: '完成周度问卷，生成康复总结', icon: '/static/icons/schedule.svg' },
        { key: 'ocr', label: 'OCR 识别', desc: '拍照识别药盒与说明书', icon: '/static/icons/ocr.svg' },
        { key: 'monitor', label: '监控', desc: '摄像头预览与跌倒检测', icon: '/static/icons/ocr.svg' },
        { key: 'profile', label: '我的', desc: '账号与提醒偏好设置', icon: '/static/icons/profile.svg' },
      ],
      currentModule: 'chat',
      sidebarExpanded: true,
      messages: [
        { id: 1, from: 'ai', text: '您好，我是康复小助手，很高兴为您服务。' },
      ],
      inputText: '',
      apiBaseUrl: APP_CONFIG.API_BASE_URL,
      monitorApiBaseUrl: APP_CONFIG.MONITOR_API_BASE,
      apiPaths: APP_CONFIG.API_PATHS,
      promptIds: APP_CONFIG.PROMPT_IDS,
      chatOptions: APP_CONFIG.CHAT_OPTIONS,
      chatHistoryOptions: APP_CONFIG.CHAT_HISTORY,
      weeklyOptions: APP_CONFIG.WEEKLY_OPTIONS,
      authRules: APP_CONFIG.AUTH_RULES,
      storageKeys: APP_CONFIG.STORAGE_KEYS,
      authToken: '',
      authUsername: '',
      chatBusy: false,
      showAiThinking: false,
      copyTextPanelVisible: false,
      copyTextContent: '',
      chatInputMode: 'text',
      voiceHoldActive: false,
      voiceHoldStartedAt: 0,
      lastModeToggleAt: 0,
      discardVoiceOnStop: false,
      audioContext: null,
      recorderManager: null,
      isRecording: false,
      recordingReady: false,
      recordingMode: 'none',
      mediaRecorder: null,
      mediaRecorderStream: null,
      mediaRecorderChunks: [],
      mediaRecordStartedAt: 0,
      voiceObjectUrls: [],
      voiceDb: null,
      chatPersistTimer: null,
      loginDialogVisible: false,
      authMode: 'login',
      authSubmitting: false,
      isUserLoggedIn: false,
      loginForm: {
        username: '',
        password: '',
        emergencyName: '',
        emergencyEmail: '',
      },
      scheduleItems: [
        {
          id: 1,
          time: '08:30',
          bp: '128/82',
          weight: '62.4kg',
          symptom: '轻微手抖',
          mood: '平稳',
          matter: '晨间用药 + 轻度拉伸',
        },
        {
          id: 2,
          time: '14:30',
          bp: '—',
          weight: '—',
          symptom: '步态平稳',
          mood: '放松',
          matter: '午后用药（14:30）',
        },
        {
          id: 3,
          time: '19:00',
          bp: '—',
          weight: '62.1kg',
          symptom: '轻度僵硬',
          mood: '略疲惫',
          matter: '步态训练 15 分钟（19:00）',
        },
      ],
      calendarMonthLabel: '2026年03月',
      calendarWeekdays: ['一', '二', '三', '四', '五', '六', '日'],
      medicationStatusMap: {
        1: true,
        2: true,
        3: false,
        4: true,
        5: true,
        6: false,
        7: true,
        8: true,
        9: true,
        10: false,
        11: true,
        12: true,
        13: false,
        14: true,
        15: true,
        16: true,
        17: false,
        18: true,
        19: true,
        20: true,
        21: false,
        22: true,
        23: true,
        24: true,
        25: false,
        26: true,
        27: true,
        28: true,
        29: false,
        30: true,
        31: true,
      },
      medicationRecordsMap: {},
      medicationMonthCache: {},
      medicationMonthCacheStorageKey: 'carepal_medication_month_cache',
      medicationCalendarCells: [],
      selectedCalendarDay: 0,
      selectedCalendarDetail: null,
      currentCalendarYear: 2026,
      currentCalendarMonth: 2,
      medicationReminderTimer: null,
      medicationReminderDateKey: '',
      medicationReminderLastMinuteKey: '',
      medicationReminderShownMap: {},
      medicationReminderStoragePrefix: 'carepal_medication_remind_',
      medicationReminderSoundEnabled: true,
      medicationReminderSoundSrc: '/sound/ding.mp3',
      medicationReminderAudioContext: null,
      calendarDrawerVisible: false,
      activeScheduleTime: '',
      activeSchedulePulse: false,
      scheduleEditDialogVisible: false,
      scheduleEditField: '',
      scheduleEditLabel: '',
      scheduleEditTime: '',
      scheduleEditValue: '',
      ocrImageUrl: '',
      ocrExplainText: '',
      ocrInputMode: 'album',
      ocrRequestTimeoutMs: (APP_CONFIG.OCR && APP_CONFIG.OCR.requestTimeoutMs) || 300000,
      ocrSubmitting: false,
      ocrImageBlob: null,
      ocrCameraVisible: false,
      ocrCameraStream: null,
      ocrCapturedObjectUrl: '',
      monitorCameraVisible: false,
      monitorCameraStream: null,
      monitorDetecting: false,
      monitorDetectionTimer: null,
      monitorRequesting: false,
      monitorStatusHint: '点击“打开摄像头”后可开始检测。',
      monitorLastResult: {
        hasFall: false,
        condition: '',
        personCount: 0,
      },
      weeklyQuestionnairePages: buildWeeklyQuestionnairePages(),
      activeWeeklyPageIndex: 0,
      currentWeekRange: '',
      weeklyManualForm: {
        scores: buildWeeklyScoreMap(),
        note: '',
      },
      weeklyAiSubmitHint: '',
      weeklyReportText: '',
      weeklyReportEncouragement: '',
      weeklyReportAudit: null,
      weeklyReportLogs: [],
      profile: {
        avatar: '',
        name: '康复小伙伴',
        phone: '13800000000',
        emergencyName: '',
        emergencyEmail: '',
      },
      editField: '',
      editValue: '',
      elderMode: false,
      darkMode: false,
    }
  },
  onLoad() {
    this.loadLocalSettings()
    this.loadMedicationMonthCacheFromStorage()
    this.currentWeekRange = this.getCurrentWeekRange()
    const savedToken = uni.getStorageSync(this.storageKeys.accessToken)
    this.authToken = typeof savedToken === 'string' ? savedToken : ''
    this.isUserLoggedIn = !!this.authToken
    const savedAuthUsername = uni.getStorageSync(this.storageKeys.authUsername)
    if (typeof savedAuthUsername === 'string' && savedAuthUsername.trim()) {
      this.authUsername = savedAuthUsername.trim()
    }
    const today = new Date()
    this.currentCalendarYear = today.getFullYear()
    this.currentCalendarMonth = today.getMonth()
    this.buildMedicationCalendar()
    this.startMedicationReminderLoop()
    this.initRecorderManager()
    this.restoreChatHistory()
  },
  onUnload() {
    this.stopMedicationReminderLoop()
    this.flushPersistChatHistory()
    if (this.chatPersistTimer) {
      clearTimeout(this.chatPersistTimer)
      this.chatPersistTimer = null
    }
    if (this.isRecording && this.recordingMode === 'uni' && this.recorderManager) {
      try {
        this.recorderManager.stop()
      } catch (error) {
      }
    }
    if (this.isRecording && this.recordingMode === 'media' && this.mediaRecorder) {
      try {
        this.mediaRecorder.stop()
      } catch (error) {
      }
    }
    this.stopMediaRecorderStream()
    this.stopOcrCameraStream()
    this.stopMonitorDetectionLoop()
    this.stopMonitorCameraStream()
    if (this.ocrCapturedObjectUrl && typeof URL !== 'undefined' && URL.revokeObjectURL) {
      URL.revokeObjectURL(this.ocrCapturedObjectUrl)
      this.ocrCapturedObjectUrl = ''
    }
    if (this.audioContext) {
      this.audioContext.stop()
      this.audioContext.destroy()
      this.audioContext = null
    }
    if (this.voiceObjectUrls.length && typeof URL !== 'undefined' && URL.revokeObjectURL) {
      this.voiceObjectUrls.forEach((url) => {
        try {
          URL.revokeObjectURL(url)
        } catch (error) {
        }
      })
      this.voiceObjectUrls = []
    }
  },
  watch: {
    messages: {
      handler() {
        this.schedulePersistChatHistory()
      },
      deep: true,
    },
    authUsername() {
      this.restoreChatHistory()
    },
    elderMode(val) {
      uni.setStorageSync('carepal_elderMode', val)
    },
    darkMode(val) {
      uni.setStorageSync('carepal_darkMode', val)
    },
  },
  computed: {
    currentModuleLabel() {
      const found = this.modules.find((item) => item.key === this.currentModule)
      return found ? found.label : '首页'
    },
    weeklyQuestionnaire() {
      return this.weeklyQuestionnairePages.reduce((acc, page) => acc.concat(page.questions || []), [])
    },
    currentWeeklyPage() {
      return this.weeklyQuestionnairePages[this.activeWeeklyPageIndex] || { title: '', questions: [] }
    },
    currentWeeklyQuestions() {
      return this.currentWeeklyPage.questions || []
    },
    displayedScheduleItems() {
      const records = (this.selectedCalendarDetail && this.selectedCalendarDetail.records) || []
      const dayCompare = this.compareCalendarDayWithToday(this.selectedCalendarDay)
      const isFutureSelectedDay = dayCompare > 0
      const isTodaySelectedDay = dayCompare === 0
      const now = new Date()
      const nowMinutes = now.getHours() * 60 + now.getMinutes()
      const recordMap = records.reduce((acc, record) => {
        acc[record.time] = record
        return acc
      }, {})

      return this.scheduleItems.map((baseItem) => {
        const record = recordMap[baseItem.time] || null
        const mergedItem = record ? { ...baseItem, ...record } : { ...baseItem }
        const hasTakenRecord = !!record && typeof record.taken === 'boolean'
        const slotMinutes = this.parseTimeToMinutes(mergedItem.time || baseItem.time)
        const isTodayElapsedSlot = isTodaySelectedDay && slotMinutes >= 0 && slotMinutes <= nowMinutes

        let medicationTag = '未记录'
        let medicationTagType = 'pending'
        if (isFutureSelectedDay) {
          medicationTag = '未记录'
          medicationTagType = 'pending'
        } else if (hasTakenRecord) {
          medicationTag = record.taken ? '已服药' : '未服药'
          medicationTagType = record.taken ? 'done' : 'miss'
        } else if (isTodayElapsedSlot) {
          medicationTag = '未服药'
          medicationTagType = 'miss'
        }

        let matterTag = '未记录'
        let matterTagType = medicationTagType
        if (medicationTagType === 'done') {
          matterTag = '正常'
        } else if (medicationTagType === 'miss') {
          matterTag = '待补服'
        }

        const medicineText =
          typeof mergedItem.medicine === 'string' && mergedItem.medicine.trim()
            ? mergedItem.medicine.trim()
            : '待补充'
        const moodText =
          typeof mergedItem.mood === 'string' && mergedItem.mood.trim()
            ? mergedItem.mood.trim()
            : '—'

        return {
          ...mergedItem,
          medicine: medicineText,
          mood: moodText,
          medicationTag,
          medicationTagType,
          matterTag,
          matterTagType,
        }
      })
    },
    calendarYearOverview() {
      const year = this.currentCalendarYear
      const today = new Date()
      return Array.from({ length: 12 }, (_, monthIndex) => {
        const monthData = this.getMedicationMonthDataSnapshot(year, monthIndex)
        const daysInMonth = new Date(year, monthIndex + 1, 0).getDate()
        const isFutureMonth =
          year > today.getFullYear() ||
          (year === today.getFullYear() && monthIndex > today.getMonth())
        const isCurrentRealMonth =
          year === today.getFullYear() &&
          monthIndex === today.getMonth()

        if (isFutureMonth) {
          return {
            monthIndex,
            label: `${monthIndex + 1}月`,
            totalDays: daysInMonth,
            takenDays: 0,
            completion: 0,
            isFutureMonth,
          }
        }

        let totalDays = 0
        let takenDays = 0
        for (let day = 1; day <= daysInMonth; day += 1) {
          if (isCurrentRealMonth && day > today.getDate()) {
            continue
          }
          totalDays += 1
          if (monthData.statusMap && monthData.statusMap[day]) {
            takenDays += 1
          }
        }

        const completion = totalDays ? takenDays / totalDays : 0
        return {
          monthIndex,
          label: `${monthIndex + 1}月`,
          totalDays,
          takenDays,
          completion,
          isFutureMonth,
        }
      })
    },
    recordingStatusText() {
      if (this.chatInputMode === 'voice') {
        if (this.isRecording) return '松开后发送语音'
        if (!this.recordingReady) return '语音不可用：请检查麦克风权限'
        return '长按输入语音，松开发送'
      }
      if (!this.recordingReady) return '录音不可用：请检查浏览器麦克风权限'
      return '点击麦克风可切换到语音输入'
    },
    displayUserName() {
      if (this.isUserLoggedIn) {
        return this.profile.name || this.authUsername || '已登录用户'
      }
      return '游客用户'
    },
    loginStatusText() {
      return this.isUserLoggedIn ? '已登录 · 点击切换账号' : '点击头像登录'
    },
  },
  methods: {
    onMicModeTrigger() {
      const now = Date.now()
      if (now - this.lastModeToggleAt < 320) return
      this.lastModeToggleAt = now
      this.toggleChatInputMode()
    },
    toggleChatInputMode() {
      this.chatInputMode = this.chatInputMode === 'text' ? 'voice' : 'text'
      if (this.chatInputMode === 'voice' && !this.recordingReady) {
        this.initRecorderManager()
        uni.showToast({ title: '已切换到长按输入语音', icon: 'none' })
      }
      if (this.chatInputMode === 'text' && this.isRecording) {
        this.stopVoiceRecording()
      }
      if (this.chatInputMode === 'text') {
        this.voiceHoldActive = false
        this.voiceHoldStartedAt = 0
      }
    },
    async onVoiceHoldStart() {
      if (this.chatInputMode !== 'voice') return
      if (this.voiceHoldActive) return
      if (this.chatBusy) {
        uni.showToast({ title: '请等待当前请求完成', icon: 'none' })
        return
      }
      if (!this.recordingReady) {
        this.initRecorderManager()
      }
      if (!this.recordingReady) {
        uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
        return
      }
      if (this.isRecording) return
      this.voiceHoldActive = true
      this.voiceHoldStartedAt = Date.now()
      this.discardVoiceOnStop = false
      await this.startVoiceRecording()
    },
    onVoiceHoldEnd() {
      if (!this.voiceHoldActive) return
      this.voiceHoldActive = false
      const holdDuration = this.voiceHoldStartedAt ? (Date.now() - this.voiceHoldStartedAt) : 0
      this.voiceHoldStartedAt = 0
      if (holdDuration < 260) {
        this.discardVoiceOnStop = true
      }
      if (this.isRecording) {
        this.stopVoiceRecording()
      } else if (holdDuration < 260) {
        uni.showToast({ title: '按住时间太短', icon: 'none' })
      }
    },
    onVoiceHoldCancel() {
      this.discardVoiceOnStop = true
      this.onVoiceHoldEnd()
    },
    openLoginDialog() {
      this.loginForm.username = ''
      this.loginForm.password = ''
      this.loginForm.emergencyName = ''
      this.loginForm.emergencyEmail = ''
      this.authMode = 'login'
      this.loginDialogVisible = true
    },
    switchAuthMode(mode) {
      this.authMode = mode === 'register' ? 'register' : 'login'
    },
    closeLoginDialog() {
      this.loginDialogVisible = false
    },
    async logout() {
      const confirmed = await new Promise((resolve) => {
        if (typeof uni.showModal !== 'function') {
          resolve(true)
          return
        }
        uni.showModal({
          title: '确认退出',
          content: '退出后将清除当前登录状态',
          success: (res) => resolve(!!(res && res.confirm)),
          fail: () => resolve(false),
        })
      })

      if (!confirmed) return
      this.authToken = ''
      this.authUsername = ''
      this.isUserLoggedIn = false
      this.loginForm.username = ''
      this.loginForm.password = ''
      this.loginForm.emergencyName = ''
      this.loginForm.emergencyEmail = ''
      uni.removeStorageSync(this.storageKeys.accessToken)
      uni.removeStorageSync(this.storageKeys.authUsername)
      this.restoreChatHistory()
      this.closeLoginDialog()
      uni.showToast({ title: '已退出登录', icon: 'success' })
    },
    validateAuthForm() {
      const username = (this.loginForm.username || '').trim()
      const password = (this.loginForm.password || '').trim()
      if (!username || !password) {
        throw new Error('请输入账号和密码')
      }
      if (password.length < this.authRules.passwordMinLength) {
        throw new Error(`密码至少 ${this.authRules.passwordMinLength} 位`)
      }
      if (username.length > this.authRules.usernameMaxLength) {
        throw new Error(`用户名最多 ${this.authRules.usernameMaxLength} 位`)
      }
      if (password.length > this.authRules.passwordMaxLength) {
        throw new Error(`密码最多 ${this.authRules.passwordMaxLength} 位`)
      }

      const emergencyName = (this.loginForm.emergencyName || '').trim()
      const emergencyEmail = (this.loginForm.emergencyEmail || '').trim()
      if (this.authMode === 'register') {
        if (!emergencyName || !emergencyEmail) {
          throw new Error('请填写紧急联系人与邮箱')
        }
        const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emergencyEmail)
        if (!validEmail) {
          throw new Error('紧急联系人邮箱格式不正确')
        }
      }
      return { username, password, emergencyName, emergencyEmail }
    },
    applyAuthSuccess(username, token) {
      this.authToken = token
      this.authUsername = username
      this.isUserLoggedIn = true
      if (!this.profile.name || this.profile.name === '康复小伙伴') {
        this.profile.name = username
      }
      uni.setStorageSync(this.storageKeys.accessToken, token)
      uni.setStorageSync(this.storageKeys.authUsername, username)
      uni.setStorageSync('carepal_profile', this.profile)
      this.restoreChatHistory()
      this.closeLoginDialog()
    },
    async submitAuth() {
      if (this.authSubmitting) return
      this.authSubmitting = true
      try {
        if (this.authMode === 'register') {
          await this.submitRegister()
          return
        }
        await this.submitLogin()
      } finally {
        this.authSubmitting = false
      }
    },
    async submitLogin() {
      try {
        const { username, password } = this.validateAuthForm()
        const loginData = await this.requestJson({
          path: this.apiPaths.login,
          method: 'POST',
          data: { username, password },
        })

        const token = (loginData && loginData.access_token) || ''
        if (!token) {
          throw new Error('登录成功但未返回 access_token')
        }

        this.applyAuthSuccess(username, token)
        uni.showToast({ title: '登录成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: (error && error.message) || '登录失败', icon: 'none' })
      }
    },
    async submitRegister() {
      try {
        const { username, password, emergencyName, emergencyEmail } = this.validateAuthForm()
        const registerData = await this.requestJson({
          path: this.apiPaths.register,
          method: 'POST',
          data: {
            username,
            password,
            emergency_contact_name: emergencyName,
            emergency_contact_email: emergencyEmail,
          },
        })
        let token = (registerData && registerData.access_token) || ''

        if (!token) {
          const loginData = await this.requestJson({
            path: this.apiPaths.login,
            method: 'POST',
            data: { username, password },
          })
          token = (loginData && loginData.access_token) || ''
        }

        if (!token) {
          throw new Error('注册成功但未返回 access_token')
        }

        this.profile.name = username
        this.profile.emergencyName = emergencyName
        this.profile.emergencyEmail = emergencyEmail

        this.applyAuthSuccess(username, token)
        uni.showToast({ title: '注册并登录成功', icon: 'success' })
      } catch (error) {
        uni.showToast({ title: (error && error.message) || '注册失败', icon: 'none' })
      }
    },
    initRecorderManager() {
      const supportMediaRecorder =
        typeof window !== 'undefined' &&
        typeof MediaRecorder !== 'undefined' &&
        typeof navigator !== 'undefined' &&
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === 'function'

      if (supportMediaRecorder) {
        this.recordingMode = 'media'
        this.recordingReady = true
        return
      }

      if (typeof uni.getRecorderManager === 'function') {
        const recorder = uni.getRecorderManager()
        this.recorderManager = recorder
        this.recordingReady = true
        this.recordingMode = 'uni'

        recorder.onStart(() => {
          this.isRecording = true
        })

        recorder.onStop((res) => {
          this.isRecording = false
          if (this.discardVoiceOnStop) {
            this.discardVoiceOnStop = false
            uni.showToast({ title: '按住时间太短', icon: 'none' })
            return
          }
          const filePath = (res && res.tempFilePath) || ''
          const durationMs = Number((res && res.duration) || 0)
          if (!filePath) {
            uni.showToast({ title: '录音文件为空', icon: 'none' })
            return
          }
          this.handleRecordedVoiceFile(filePath, durationMs)
        })

        recorder.onError(() => {
          this.isRecording = false
          uni.showToast({ title: '录音失败', icon: 'none' })
        })
        return
      }

      this.recordingReady = false
      this.recordingMode = 'none'
    },
    requestRecordPermission() {
      return new Promise((resolve, reject) => {
        if (typeof uni.authorize !== 'function') {
          resolve(true)
          return
        }
        uni.authorize({
          scope: 'scope.record',
          success: () => resolve(true),
          fail: (err) => reject(err || new Error('录音权限申请失败')),
        })
      })
    },
    async startVoiceRecording() {
      const canUseMedia =
        typeof window !== 'undefined' &&
        typeof MediaRecorder !== 'undefined' &&
        typeof navigator !== 'undefined' &&
        navigator.mediaDevices &&
        typeof navigator.mediaDevices.getUserMedia === 'function'

      if (this.recordingMode !== 'media' && canUseMedia) {
        this.recordingMode = 'media'
      }

      if (this.recordingMode === 'media') {
        await this.startMediaRecorder()
        return
      }

      if (this.recordingMode !== 'uni' || !this.recorderManager) return
      try {
        await this.requestRecordPermission()
        this.recorderManager.start({
          duration: 60000,
          sampleRate: 16000,
          numberOfChannels: 1,
          encodeBitRate: 96000,
          format: 'mp3',
          frameSize: 50,
        })
        uni.showToast({ title: '开始录音，松开发送', icon: 'none' })

        // 某些 H5 环境会暴露 uni 录音接口但实际不可用，超时后自动回退到浏览器录音。
        setTimeout(async () => {
          if (this.recordingMode !== 'uni' || this.isRecording) return
          const canUseMedia =
            typeof window !== 'undefined' &&
            typeof MediaRecorder !== 'undefined' &&
            typeof navigator !== 'undefined' &&
            navigator.mediaDevices &&
            typeof navigator.mediaDevices.getUserMedia === 'function'
          if (!canUseMedia) {
            uni.showToast({ title: '录音器未启动，请检查权限', icon: 'none' })
            return
          }
          this.recordingMode = 'media'
          uni.showToast({ title: '已切换浏览器录音', icon: 'none' })
          await this.startMediaRecorder()
        }, 1200)
      } catch (error) {
        uni.showToast({ title: '请先允许麦克风权限', icon: 'none' })
      }
    },
    stopVoiceRecording() {
      if (this.recordingMode === 'media') {
        if (!this.mediaRecorder) return
        this.mediaRecorder.stop()
        uni.showToast({ title: '录音结束，正在上传', icon: 'none' })
        return
      }

      if (this.recordingMode !== 'uni' || !this.recorderManager) return
      this.recorderManager.stop()
      uni.showToast({ title: '录音结束，正在上传', icon: 'none' })
    },
    stopMediaRecorderStream() {
      if (!this.mediaRecorderStream) return
      this.mediaRecorderStream.getTracks().forEach((track) => track.stop())
      this.mediaRecorderStream = null
    },
    getMediaRecorderMimeType() {
      if (typeof MediaRecorder === 'undefined' || typeof MediaRecorder.isTypeSupported !== 'function') {
        return ''
      }
      const mimeTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
      const found = mimeTypes.find((type) => MediaRecorder.isTypeSupported(type))
      return found || ''
    },
    encodeWavFromAudioBuffer(audioBuffer) {
      const numberOfChannels = audioBuffer.numberOfChannels
      const sampleRate = audioBuffer.sampleRate
      const bitDepth = 16

      const channelData = []
      for (let i = 0; i < numberOfChannels; i += 1) {
        channelData.push(audioBuffer.getChannelData(i))
      }

      const length = audioBuffer.length
      const bytesPerSample = bitDepth / 8
      const blockAlign = numberOfChannels * bytesPerSample
      const dataSize = length * blockAlign
      const buffer = new ArrayBuffer(44 + dataSize)
      const view = new DataView(buffer)

      const writeString = (offset, str) => {
        for (let i = 0; i < str.length; i += 1) {
          view.setUint8(offset + i, str.charCodeAt(i))
        }
      }

      writeString(0, 'RIFF')
      view.setUint32(4, 36 + dataSize, true)
      writeString(8, 'WAVE')
      writeString(12, 'fmt ')
      view.setUint32(16, 16, true)
      view.setUint16(20, 1, true)
      view.setUint16(22, numberOfChannels, true)
      view.setUint32(24, sampleRate, true)
      view.setUint32(28, sampleRate * blockAlign, true)
      view.setUint16(32, blockAlign, true)
      view.setUint16(34, bitDepth, true)
      writeString(36, 'data')
      view.setUint32(40, dataSize, true)

      let offset = 44
      for (let sampleIndex = 0; sampleIndex < length; sampleIndex += 1) {
        for (let channelIndex = 0; channelIndex < numberOfChannels; channelIndex += 1) {
          const sample = channelData[channelIndex][sampleIndex] || 0
          const clamped = Math.max(-1, Math.min(1, sample))
          const int16 = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
          view.setInt16(offset, int16, true)
          offset += 2
        }
      }

      return buffer
    },
    async resampleAudioBuffer(audioBuffer, targetSampleRate = 16000) {
      if (!audioBuffer || !audioBuffer.sampleRate) {
        throw new Error('音频数据无效')
      }
      if (audioBuffer.sampleRate === targetSampleRate) {
        return audioBuffer
      }

      const OfflineAudioContextCtor =
        (typeof window !== 'undefined' &&
          (window.OfflineAudioContext || window.webkitOfflineAudioContext)) ||
        null
      if (!OfflineAudioContextCtor) {
        throw new Error('当前浏览器不支持音频重采样')
      }

      const targetLength = Math.ceil(audioBuffer.duration * targetSampleRate)
      const offlineContext = new OfflineAudioContextCtor(
        audioBuffer.numberOfChannels,
        targetLength,
        targetSampleRate
      )
      const source = offlineContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(offlineContext.destination)
      source.start(0)
      return offlineContext.startRendering()
    },
    async convertMediaBlobToWav(blob) {
      if (!blob || !blob.size) {
        throw new Error('录音文件为空')
      }
      const AudioContextCtor =
        (typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)) || null
      if (!AudioContextCtor) {
        throw new Error('当前浏览器不支持音频转换')
      }

      const sourceBuffer = typeof blob.arrayBuffer === 'function'
        ? await blob.arrayBuffer()
        : await new Response(blob).arrayBuffer()

      const audioContext = new AudioContextCtor()
      try {
        const decoded = await new Promise((resolve, reject) => {
          audioContext.decodeAudioData(sourceBuffer.slice(0), resolve, reject)
        })
        const resampled = await this.resampleAudioBuffer(decoded, 16000)
        const wavArrayBuffer = this.encodeWavFromAudioBuffer(resampled)
        return new Blob([wavArrayBuffer], { type: 'audio/wav' })
      } catch (error) {
        throw new Error('录音格式转换失败，请重试')
      } finally {
        if (typeof audioContext.close === 'function') {
          try {
            await audioContext.close()
          } catch (e) {
            // ignore
          }
        }
      }
    },
    async startMediaRecorder() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        const mimeType = this.getMediaRecorderMimeType()
        const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)

        this.mediaRecorderStream = stream
        this.mediaRecorder = recorder
        this.mediaRecorderChunks = []

        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.mediaRecorderChunks.push(event.data)
          }
        }

        recorder.onstart = () => {
          this.isRecording = true
          this.mediaRecordStartedAt = Date.now()
        }

        recorder.onerror = () => {
          this.isRecording = false
          this.stopMediaRecorderStream()
          uni.showToast({ title: '录音失败', icon: 'none' })
        }

        recorder.onstop = async () => {
          this.isRecording = false
          if (this.discardVoiceOnStop) {
            this.discardVoiceOnStop = false
            this.mediaRecorderChunks = []
            this.mediaRecorder = null
            this.stopMediaRecorderStream()
            uni.showToast({ title: '按住时间太短', icon: 'none' })
            return
          }
          const durationMs = this.mediaRecordStartedAt ? (Date.now() - this.mediaRecordStartedAt) : 0
          this.mediaRecordStartedAt = 0
          const chunks = this.mediaRecorderChunks || []
          const blobType = recorder.mimeType || 'audio/webm'
          const audioBlob = chunks.length ? new Blob(chunks, { type: blobType }) : null
          this.mediaRecorderChunks = []
          this.mediaRecorder = null
          this.stopMediaRecorderStream()

          if (!audioBlob || audioBlob.size === 0) {
            uni.showToast({ title: '录音文件为空', icon: 'none' })
            return
          }
          await this.handleRecordedVoiceBlob(audioBlob, durationMs)
        }

        recorder.start()
        uni.showToast({ title: '开始录音，松开发送', icon: 'none' })
      } catch (error) {
        this.isRecording = false
        this.stopMediaRecorderStream()
        const errText = (error && error.message) || ''
        const denied = /denied|permission|NotAllowedError|不允许/i.test(errText)
        uni.showToast({ title: denied ? '请先允许麦克风权限' : '无法调用麦克风', icon: 'none' })
      }
    },
    uploadVoiceBlobWithText(audioBlob, fileName) {
      return new Promise((resolve, reject) => {
        if (typeof FormData === 'undefined' || typeof fetch === 'undefined') {
          reject(new Error('当前环境不支持浏览器录音上传'))
          return
        }

        const formData = new FormData()
        formData.append('audio', audioBlob, fileName)
        formData.append('with_text', 'true')
        formData.append('with_audio', String(this.chatOptions.withAudio))
        formData.append('prompt', String(this.promptIds.chatAssistant))

        fetch(this.apiUrl(this.apiPaths.chatVoice), {
          method: 'POST',
          headers: this.buildAuthHeader(),
          body: formData,
        })
          .then(async (res) => {
            if (!res.ok) {
              if (res.status === 401) {
                this.handleUnauthorized('登录已失效，请重新登录')
              }
              reject(new Error(`语音上传失败(${res.status})`))
              return
            }
            try {
              const json = await res.json()
              resolve(json || {})
            } catch (error) {
              reject(new Error('语音接口返回格式异常'))
            }
          })
          .catch((error) => {
            reject(new Error((error && error.message) || '语音上传失败'))
          })
      })
    },
    async handleRecordedVoiceFile(filePath, durationMs = 0) {
      this.chatBusy = true
      this.showAiThinking = true
      const savedPath = await this.saveVoiceFileToPersistentPath(filePath)
      const stablePath = savedPath || filePath
      const userVoiceMsg = this.buildUserVoiceMessage(stablePath, '', durationMs, {
        voiceStorageType: savedPath ? 'saved-file' : 'temp-file',
        voiceStorageKey: savedPath || '',
      })
      this.messages.push(userVoiceMsg)
      try {
        await this.ensureAuthToken()
        const result = await this.uploadVoiceWithText(filePath, `voice_${Date.now()}.mp3`)
        const asrText = (result && result.asr_text) || ''
        const assistantText = await this.normalizeAssistantReply(result)
        const audioFileUrl = (result && result.audio_file_url) || ''

        userVoiceMsg.transcript = asrText
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: assistantText || '语音接口未返回回复文本',
          audioFileUrl,
        })
        this.showAiThinking = false

        if (audioFileUrl) {
          await this.downloadAndPlayVoice(audioFileUrl)
        }
      } catch (error) {
        this.showAiThinking = false
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: `语音调用失败：${(error && error.message) || '未知错误'}`,
        })
      } finally {
        this.chatBusy = false
        this.showAiThinking = false
      }
    },
    async handleRecordedVoiceBlob(audioBlob, durationMs = 0) {
      this.chatBusy = true
      this.showAiThinking = true
      let voiceSrc = ''
      let voiceStorageType = ''
      let voiceStorageKey = ''
      if (typeof URL !== 'undefined' && URL.createObjectURL) {
        voiceSrc = URL.createObjectURL(audioBlob)
        this.voiceObjectUrls.push(voiceSrc)
      }
      try {
        voiceStorageKey = `voice_${Date.now()}_${Math.floor(Math.random() * 1000)}`
        await this.putVoiceBlobToDb(voiceStorageKey, audioBlob)
        voiceStorageType = 'idb'
      } catch (error) {
        voiceStorageType = 'memory'
        voiceStorageKey = ''
      }
      const userVoiceMsg = this.buildUserVoiceMessage(voiceSrc, '', durationMs, {
        voiceStorageType,
        voiceStorageKey,
      })
      this.messages.push(userVoiceMsg)
      try {
        await this.ensureAuthToken()
        const wavBlob = await this.convertMediaBlobToWav(audioBlob)
        const result = await this.uploadVoiceBlobWithText(wavBlob, `voice_${Date.now()}.wav`)
        const asrText = (result && result.asr_text) || ''
        const assistantText = await this.normalizeAssistantReply(result)
        const audioFileUrl = (result && result.audio_file_url) || ''

        userVoiceMsg.transcript = asrText
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: assistantText || '语音接口未返回回复文本',
          audioFileUrl,
        })
        this.showAiThinking = false

        if (audioFileUrl) {
          await this.downloadAndPlayVoice(audioFileUrl)
        }
      } catch (error) {
        this.showAiThinking = false
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: `语音调用失败：${(error && error.message) || '未知错误'}`,
        })
      } finally {
        this.chatBusy = false
        this.showAiThinking = false
      }
    },
    getCurrentWeekRange() {
      const today = new Date()
      const day = today.getDay()
      const diffToMonday = day === 0 ? 6 : day - 1
      const monday = new Date(today)
      monday.setDate(today.getDate() - diffToMonday)
      const sunday = new Date(monday)
      sunday.setDate(monday.getDate() + 6)
      const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      return `${fmt(monday)} 至 ${fmt(sunday)}`
    },
    buildWeeklyReportMessage() {
      const scoreLines = []
      this.weeklyQuestionnairePages.forEach((page) => {
        scoreLines.push(`【${page.title}】`)
        page.questions.forEach((question) => {
          const score = this.weeklyManualForm.scores[question.id]
          scoreLines.push(`${question.code} ${question.title}: ${score}`)
        })
      })
      const note = (this.weeklyManualForm.note || '').trim()
      return [
        `周区间：${this.currentWeekRange}`,
        '问卷分数：',
        ...scoreLines,
        `补充说明：${note || '无'}`,
        '请基于以上数据生成周报告建议。',
      ].join('\n')
    },
    /**
     * Build user-facing payload source label for weekly audit panel.
     * @param {'assistant_payload'|'assistant_text_json'|'none'|string} payloadSource - Source key of the parsed weekly payload.
     * @returns {string} Human-readable label shown in UI.
     * Convert internal payload source key into a Chinese label for display.
     */
    buildWeeklyPayloadSourceLabel(payloadSource) {
      if (payloadSource === 'assistant_payload') return 'assistant_payload（对象）'
      if (payloadSource === 'assistant_text_json') return 'assistant_text（提取 JSON）'
      return '未识别结构化数据'
    },
    /**
     * Clone weekly log data into JSON-safe plain object.
     * @param {any} value - Any runtime object/value captured in weekly log.
     * @returns {any} Deep-cloned JSON-safe value, or null when cloning fails.
     * Avoid logging reactive references and ensure log snapshot stays stable.
     */
    cloneWeeklyLogData(value) {
      try {
        return JSON.parse(JSON.stringify(value))
      } catch (error) {
        return null
      }
    },
    /**
     * Push a weekly report log entry and keep only recent entries.
     * @param {Object} logEntry - Structured log object for one weekly report generation attempt.
     * @returns {void} No return value.
     * Store log snapshot in memory and print to console for debugging.
     */
    pushWeeklyReportLog(logEntry) {
      const entry = this.cloneWeeklyLogData(logEntry) || {}
      this.weeklyReportLogs = [entry, ...this.weeklyReportLogs].slice(0, 30)
      if (typeof console !== 'undefined' && typeof console.log === 'function') {
        console.log('[WeeklyReport]', entry)
      }
    },
    /**
     * Audit and normalize weekly report payload based on agent JSON contract.
     * @param {Object|null} payload - Raw JSON object from assistant_payload or parsed assistant_text.
     * @returns {{normalized: ({week_range: string, overall_level: string, total_score: string, avg_score: string, top_issues: Array<{question_id: string, question: string, score: string}>, this_week_focus: string[], daily_actions: string[], risk_warnings: string[], medical_followup: string, encouragement: string, _audit: Object, _isNormalized: boolean}|null), audit: Object}} Normalized payload and audit result.
     * Validate nested JSON structure, record missing/type issues, and produce normalized fields for template rendering.
     */
    auditAndNormalizeWeeklyReportPayload(payload) {
      const expectedFieldPaths = [
        'week_range',
        'overall_level',
        'score_summary.total_score',
        'score_summary.avg_score',
        'score_summary.top_issues',
        'advice.this_week_focus',
        'advice.daily_actions',
        'advice.risk_warnings',
        'advice.medical_followup',
        'encouragement',
      ]
      const audit = {
        payloadSource: 'none',
        payloadSourceLabel: this.buildWeeklyPayloadSourceLabel('none'),
        expectedFieldCount: expectedFieldPaths.length,
        receivedFieldCount: 0,
        missingFields: [],
        emptyFields: [],
        typeErrors: [],
        nonStandardHits: [],
        matchedFieldPaths: [],
        status: 'invalid',
      }

      if (!payload || typeof payload !== 'object') {
        audit.missingFields = [...expectedFieldPaths]
        return { normalized: null, audit }
      }

      const hasValue = (value) => value !== undefined && value !== null
      const uniqueList = (list) => [...new Set((Array.isArray(list) ? list : []).filter((item) => typeof item === 'string' && item.trim()))]
      const matchedFieldSet = new Set()

      const scoreSummary = hasValue(payload.score_summary) && typeof payload.score_summary === 'object' ? payload.score_summary : null
      const advice = hasValue(payload.advice) && typeof payload.advice === 'object' ? payload.advice : null

      if (hasValue(payload.score_summary) && !scoreSummary) {
        audit.typeErrors.push('score_summary 应为对象')
      }
      if (hasValue(payload.advice) && !advice) {
        audit.typeErrors.push('advice 应为对象')
      }

      const pickField = (primaryValue, fallbackValue, expectedPath, fallbackPath) => {
        if (hasValue(primaryValue)) {
          matchedFieldSet.add(expectedPath)
          return primaryValue
        }
        if (hasValue(fallbackValue)) {
          matchedFieldSet.add(expectedPath)
          audit.nonStandardHits.push(`${fallbackPath} -> ${expectedPath}`)
          return fallbackValue
        }
        return undefined
      }

      const toText = (value, expectedPath, fallback = '无') => {
        if (typeof value === 'string') {
          const text = value.trim()
          if (!text) {
            audit.emptyFields.push(expectedPath)
            return fallback
          }
          return text
        }
        if (typeof value === 'number' || typeof value === 'boolean') {
          return String(value)
        }
        if (hasValue(value)) {
          audit.typeErrors.push(`${expectedPath} 应为字符串/数字/布尔值`)
        }
        return fallback
      }

      const toStringList = (value, expectedPath) => {
        if (Array.isArray(value)) {
          const list = value
            .map((item) => {
              if (typeof item === 'string') return item.trim()
              if (typeof item === 'number' || typeof item === 'boolean') return String(item)
              return ''
            })
            .filter((item) => !!item)
          if (!list.length) {
            audit.emptyFields.push(expectedPath)
          }
          return list
        }
        if (typeof value === 'string') {
          const text = value.trim()
          if (!text) {
            audit.emptyFields.push(expectedPath)
            return []
          }
          return [text]
        }
        if (typeof value === 'number' || typeof value === 'boolean') {
          return [String(value)]
        }
        if (hasValue(value)) {
          audit.typeErrors.push(`${expectedPath} 应为数组或字符串`)
        }
        return []
      }

      const toTopIssues = (value, expectedPath) => {
        if (!Array.isArray(value)) {
          if (hasValue(value)) {
            audit.typeErrors.push(`${expectedPath} 应为数组`)
          }
          return []
        }
        if (!value.length) {
          audit.emptyFields.push(expectedPath)
          return []
        }

        const normalizedIssues = value
          .map((item, index) => {
            const itemPath = `${expectedPath}[${index}]`
            if (!item || typeof item !== 'object') {
              audit.typeErrors.push(`${itemPath} 应为对象`)
              return null
            }
            if (!hasValue(item.question_id)) {
              audit.typeErrors.push(`${itemPath}.question_id 缺失`)
            }
            if (!hasValue(item.question)) {
              audit.typeErrors.push(`${itemPath}.question 缺失`)
            }
            if (!hasValue(item.score)) {
              audit.typeErrors.push(`${itemPath}.score 缺失`)
            }

            return {
              question_id: toText(item.question_id, `${itemPath}.question_id`),
              question: toText(item.question, `${itemPath}.question`),
              score: toText(item.score, `${itemPath}.score`),
            }
          })
          .filter((item) => !!item)

        if (!normalizedIssues.length) {
          audit.emptyFields.push(expectedPath)
        }
        return normalizedIssues
      }

      const weekRangeRaw = pickField(payload.week_range, undefined, 'week_range', 'week_range')
      const overallLevelRaw = pickField(payload.overall_level, undefined, 'overall_level', 'overall_level')
      const totalScoreRaw = pickField(scoreSummary && scoreSummary.total_score, payload.total_score, 'score_summary.total_score', 'total_score')
      const avgScoreRaw = pickField(scoreSummary && scoreSummary.avg_score, payload.avg_score, 'score_summary.avg_score', 'avg_score')
      const topIssuesRaw = pickField(scoreSummary && scoreSummary.top_issues, payload.top_issues, 'score_summary.top_issues', 'top_issues')
      const thisWeekFocusRaw = pickField(advice && advice.this_week_focus, payload.this_week_focus, 'advice.this_week_focus', 'this_week_focus')
      const dailyActionsRaw = pickField(advice && advice.daily_actions, payload.daily_actions, 'advice.daily_actions', 'daily_actions')
      const riskWarningsRaw = pickField(advice && advice.risk_warnings, payload.risk_warnings, 'advice.risk_warnings', 'risk_warnings')
      const medicalFollowupRaw = pickField(advice && advice.medical_followup, payload.medical_followup, 'advice.medical_followup', 'medical_followup')
      const encouragementRaw = pickField(payload.encouragement, advice && advice.encouragement, 'encouragement', 'advice.encouragement')

      const normalized = {
        week_range: toText(weekRangeRaw, 'week_range'),
        overall_level: toText(overallLevelRaw, 'overall_level'),
        total_score: toText(totalScoreRaw, 'score_summary.total_score'),
        avg_score: toText(avgScoreRaw, 'score_summary.avg_score'),
        top_issues: toTopIssues(topIssuesRaw, 'score_summary.top_issues'),
        this_week_focus: toStringList(thisWeekFocusRaw, 'advice.this_week_focus'),
        daily_actions: toStringList(dailyActionsRaw, 'advice.daily_actions'),
        risk_warnings: toStringList(riskWarningsRaw, 'advice.risk_warnings'),
        medical_followup: toText(medicalFollowupRaw, 'advice.medical_followup'),
        encouragement: toText(encouragementRaw, 'encouragement'),
        _isNormalized: true,
      }

      audit.matchedFieldPaths = Array.from(matchedFieldSet)
      audit.missingFields = expectedFieldPaths.filter((path) => !matchedFieldSet.has(path))
      audit.emptyFields = uniqueList(audit.emptyFields)
      audit.typeErrors = uniqueList(audit.typeErrors)
      audit.nonStandardHits = uniqueList(audit.nonStandardHits)
      audit.receivedFieldCount = audit.expectedFieldCount - audit.missingFields.length

      if (!audit.missingFields.length && !audit.typeErrors.length && !audit.emptyFields.length) {
        audit.status = 'ok'
      } else if (audit.receivedFieldCount > 0) {
        audit.status = 'partial'
      } else {
        audit.status = 'invalid'
      }

      if (!audit.receivedFieldCount) {
        return { normalized: null, audit }
      }

      return {
        normalized: {
          ...normalized,
          _audit: audit,
        },
        audit,
      }
    },
    /**
     * Build the final weekly report template text from normalized JSON fields.
     * @param {{week_range: string, overall_level: string, total_score: string, avg_score: string, top_issues: Array<{question_id: string, question: string, score: string}>, this_week_focus: string[], daily_actions: string[], risk_warnings: string[], medical_followup: string, encouragement: string, _isNormalized: boolean}|null} report - Normalized weekly report object.
     * @returns {{mainText: string, encouragementText: string}|null} Template text result for rendering, null when payload cannot be used.
     * Generate the user-facing weekly report body in fixed order and keep encouragement as a standalone block.
     */
    buildWeeklyReportTemplate(report) {
      if (!report || !report._isNormalized) return null

      const topIssueLines = report.top_issues.length
        ? report.top_issues.map((item) => `- 题目ID：${item.question_id}，问题：${item.question}，分数：${item.score}`).join('\n')
        : '- 无'
      const focusLines = report.this_week_focus.length
        ? report.this_week_focus.map((item) => `- ${item}`).join('\n')
        : '- 无'
      const actionLines = report.daily_actions.length
        ? report.daily_actions.map((item) => `- ${item}`).join('\n')
        : '- 无'
      const riskLines = report.risk_warnings.length
        ? report.risk_warnings.map((item) => `- ${item}`).join('\n')
        : '- 无'

      const mainText = [
        `周报周期：${report.week_range}`,
        '',
        `整体风险水平：${report.overall_level}`,
        '',
        '分数总结',
        `总分：${report.total_score}`,
        `平均分：${report.avg_score}`,
        '',
        '主要问题：',
        topIssueLines,
        '',
        '建议',
        '',
        '本周重点：',
        focusLines,
        '',
        '每日行动建议：',
        actionLines,
        '',
        '风险提醒：',
        riskLines,
        '',
        '医疗随访建议：',
        report.medical_followup,
      ].join('\n')

      return {
        mainText,
        encouragementText: report.encouragement,
      }
    },
    /**
     * Submit weekly questionnaire, record response logs, and render safe weekly report output.
     * @param {void} noParam - This method does not accept parameters.
     * @returns {Promise<void>} Promise resolved after submission, parsing, auditing, and rendering.
     * Ensure structured payload is audited and prevent raw formatted response from being shown to end users.
     */
    async submitWeeklyQuestionnaireToAi() {
      const unanswered = this.weeklyQuestionnaire.find((question) => this.weeklyManualForm.scores[question.id] === null)
      if (unanswered) {
        uni.showToast({ title: `请完成第${unanswered.code}题评分`, icon: 'none' })
        return
      }

      this.weeklyReportAudit = null
      this.weeklyAiSubmitHint = `已提交 ${this.currentWeekRange} 问卷，正在生成报告...`
      const weeklyLog = {
        timestamp: new Date().toISOString(),
        weekRange: this.currentWeekRange,
        promptId: this.promptIds.weeklyAssistant,
        payloadSource: 'none',
        rawResponse: null,
        assistantText: '',
        assistantPayload: null,
        extractedPayload: null,
        audit: null,
        status: 'pending',
        renderMode: '',
        errorMessage: '',
      }

      try {
        await this.ensureAuthToken()
        const response = await this.requestJson({
          path: this.apiPaths.chatText,
          method: 'POST',
          data: {
            message: this.buildWeeklyReportMessage(),
            prompt: this.promptIds.weeklyAssistant,
            with_text: this.weeklyOptions.withText,
            with_audio: this.weeklyOptions.withAudio,
          },
          withAuth: true,
        })
        weeklyLog.rawResponse = this.cloneWeeklyLogData(response)

        const rawWeeklyReply = (response && (response.assistant_text || response.answer)) || ''
        weeklyLog.assistantText = rawWeeklyReply

        const assistantPayload = response && response.assistant_payload && typeof response.assistant_payload === 'object'
          ? response.assistant_payload
          : null
        weeklyLog.assistantPayload = this.cloneWeeklyLogData(assistantPayload)

        let weeklyPayload = null
        if (assistantPayload) {
          weeklyPayload = assistantPayload
          weeklyLog.payloadSource = 'assistant_payload'
        } else {
          const parsedFromText = this.extractJsonPayload(rawWeeklyReply)
          if (parsedFromText && typeof parsedFromText === 'object') {
            weeklyPayload = parsedFromText
            weeklyLog.payloadSource = 'assistant_text_json'
          }
        }

        weeklyLog.extractedPayload = this.cloneWeeklyLogData(weeklyPayload)

        const normalizedResult = this.auditAndNormalizeWeeklyReportPayload(weeklyPayload)
        const audit = normalizedResult.audit || {
          payloadSource: 'none',
          payloadSourceLabel: this.buildWeeklyPayloadSourceLabel('none'),
          expectedFieldCount: 10,
          receivedFieldCount: 0,
          missingFields: [],
          emptyFields: [],
          typeErrors: [],
          nonStandardHits: [],
          matchedFieldPaths: [],
          status: 'invalid',
        }

        audit.payloadSource = weeklyLog.payloadSource
        audit.payloadSourceLabel = this.buildWeeklyPayloadSourceLabel(weeklyLog.payloadSource)
        this.weeklyReportAudit = audit
        weeklyLog.audit = this.cloneWeeklyLogData(audit)

        const weeklyTemplate = this.buildWeeklyReportTemplate(normalizedResult.normalized)

        if (weeklyTemplate) {
          this.weeklyReportText = weeklyTemplate.mainText
          this.weeklyReportEncouragement = weeklyTemplate.encouragementText
          this.weeklyAiSubmitHint = `已生成 ${this.currentWeekRange} 周报告`
          weeklyLog.status = 'success'
          weeklyLog.renderMode = 'template'
          this.pushWeeklyReportLog(weeklyLog)
          uni.showToast({ title: '周报告已生成', icon: 'success' })
        } else {
          this.weeklyReportText = '周报告已生成，但返回数据结构未命中模板，已记录报文供排查。'
          this.weeklyReportEncouragement = ''
          this.weeklyAiSubmitHint = `已收到 ${this.currentWeekRange} 报文，字段需检查`
          weeklyLog.status = 'partial'
          weeklyLog.renderMode = 'safe-fallback'
          this.pushWeeklyReportLog(weeklyLog)
          uni.showToast({ title: '周报告字段需检查', icon: 'none' })
        }
      } catch (error) {
        this.weeklyAiSubmitHint = ''
        this.weeklyReportText = '周报告生成失败，请稍后重试。'
        this.weeklyReportEncouragement = ''

        if (!this.weeklyReportAudit) {
          this.weeklyReportAudit = {
            payloadSource: 'none',
            payloadSourceLabel: this.buildWeeklyPayloadSourceLabel('none'),
            expectedFieldCount: 10,
            receivedFieldCount: 0,
            missingFields: [],
            emptyFields: [],
            typeErrors: [((error && error.message) || '生成周报告失败')],
            nonStandardHits: [],
            matchedFieldPaths: [],
            status: 'error',
          }
        }

        weeklyLog.status = 'error'
        weeklyLog.renderMode = 'error'
        weeklyLog.errorMessage = (error && error.message) || '生成周报告失败'
        weeklyLog.audit = this.cloneWeeklyLogData(this.weeklyReportAudit)
        this.pushWeeklyReportLog(weeklyLog)
        uni.showToast({ title: (error && error.message) || '生成周报告失败', icon: 'none' })
      }
    },
    apiUrl(path) {
      return `${this.apiBaseUrl}${path}`
    },
    monitorApiUrl(path) {
      return `${this.monitorApiBaseUrl}${path}`
    },
    buildMessageId() {
      return Date.now() + Math.floor(Math.random() * 1000)
    },
    tryParseJsonObject(rawText) {
      if (typeof rawText !== 'string') return null
      const text = rawText.trim()
      if (!text) return null
      try {
        const parsed = JSON.parse(text)
        return parsed && typeof parsed === 'object' ? parsed : null
      } catch (error) {
        return null
      }
    },
    extractJsonPayload(rawReply) {
      if (rawReply && typeof rawReply === 'object') {
        return rawReply
      }
      if (typeof rawReply !== 'string') return null
      const text = rawReply.trim()
      if (!text) return null

      const direct = this.tryParseJsonObject(text)
      if (direct) return direct

      const fenced = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i)
      if (fenced && fenced[1]) {
        const parsedFenced = this.tryParseJsonObject(fenced[1])
        if (parsedFenced) return parsedFenced
      }

      const firstObj = text.match(/\{[\s\S]*\}/)
      if (firstObj && firstObj[0]) {
        const parsedObj = this.tryParseJsonObject(firstObj[0])
        if (parsedObj) return parsedObj
      }

      return null
    },
    confirmScheduleEdit(payload) {
      const targetDate = (payload && payload.schedule_action && payload.schedule_action.target_date) || '今天'
      return new Promise((resolve) => {
        if (typeof uni.showModal !== 'function') {
          resolve(true)
          return
        }
        uni.showModal({
          title: '确认修改日程',
          content: `是否应用本次日程修改？（${targetDate}）`,
          success: (res) => resolve(!!(res && res.confirm)),
          fail: () => resolve(false),
        })
      })
    },
    pickScheduleDay(targetDate) {
      if (!targetDate || typeof targetDate !== 'string') return this.selectedCalendarDay || 1
      const match = targetDate.match(/^(\d{4})-(\d{2})-(\d{2})$/)
      if (!match) return this.selectedCalendarDay || 1
      const year = Number(match[1])
      const month = Number(match[2]) - 1
      const day = Number(match[3])
      if (year === this.currentCalendarYear && month === this.currentCalendarMonth) {
        return day
      }
      return this.selectedCalendarDay || 1
    },
    upsertBaseScheduleRow(time, data = {}) {
      if (!time) return
      const idx = this.scheduleItems.findIndex((item) => item.time === time)
      const patch = {}
      if (typeof data.bp === 'string' && data.bp.trim()) patch.bp = data.bp.trim()
      if (typeof data.weight === 'string' && data.weight.trim()) patch.weight = data.weight.trim()
      if (typeof data.symptom === 'string' && data.symptom.trim()) patch.symptom = data.symptom.trim()
      if (typeof data.mood === 'string' && data.mood.trim()) patch.mood = data.mood.trim()
      if (typeof data.matter === 'string' && data.matter.trim()) patch.matter = data.matter.trim()
      if (!Object.keys(patch).length) return

      if (idx >= 0) {
        this.scheduleItems[idx] = { ...this.scheduleItems[idx], ...patch }
        return
      }

      this.scheduleItems.push({
        id: this.buildMessageId(),
        time,
        bp: patch.bp || '—',
        weight: patch.weight || '—',
        symptom: patch.symptom || '—',
        mood: patch.mood || '—',
        matter: patch.matter || '待补充',
      })
      this.scheduleItems.sort((a, b) => String(a.time).localeCompare(String(b.time)))
    },
    toTakenFlag(data = {}) {
      if (typeof data.taken === 'boolean') return data.taken
      if (data.medicationTagType === 'done') return true
      if (data.medicationTagType === 'miss') return false
      return false
    },
    applyScheduleAction(scheduleAction) {
      if (!scheduleAction || scheduleAction.type !== 'schedule_update') return false
      const operations = Array.isArray(scheduleAction.operations) ? scheduleAction.operations : []
      if (!operations.length) return false

      const day = this.pickScheduleDay(scheduleAction.target_date)
      const records = Array.isArray(this.medicationRecordsMap[day])
        ? this.medicationRecordsMap[day].map((item) => ({ ...item }))
        : []

      operations.forEach((operation) => {
        const op = (operation && operation.op) || 'update'
        const data = (operation && operation.data) || {}
        const match = (operation && operation.match) || {}
        const time = (data.time || match.time || '').trim()
        if (!time) return

        const idx = records.findIndex((item) => item.time === time)
        if (op === 'delete') {
          if (idx >= 0) records.splice(idx, 1)
          return
        }

        const nextRecord = {
          time,
          medicine: (data.medicine || (idx >= 0 ? records[idx].medicine : '待补充')),
          mood: (typeof data.mood === 'string' && data.mood.trim()) ? data.mood.trim() : (idx >= 0 && records[idx].mood ? records[idx].mood : ''),
          taken: this.toTakenFlag(data),
        }

        if (idx >= 0) {
          records[idx] = { ...records[idx], ...nextRecord }
        } else {
          records.push(nextRecord)
        }

        this.upsertBaseScheduleRow(time, data)
      })

      records.sort((a, b) => String(a.time).localeCompare(String(b.time)))
      this.medicationRecordsMap[day] = records
      this.updateDayMedicationStatus(day, records)

      if (this.selectedCalendarDay === day) {
        this.selectedCalendarDetail = this.buildSelectedDayDetail(day)
      }
      this.persistCurrentMonthDataToCache()
      this.rebuildMedicationCalendarCells()
      this.updateMedicationStatusHint()
      return true
    },
    async normalizeAssistantReply(response) {
      const rawReply =
        (response &&
          (response.reply_text || response.assistant_text || response.response || response.text || response.answer)) ||
        ''
      const payload = this.extractJsonPayload(rawReply)

      if (payload && typeof payload === 'object') {
        if (payload.intent === 'schedule_edit' && payload.schedule_action) {
          const confirmed = await this.confirmScheduleEdit(payload)
          if (!confirmed) {
            return '已取消本次日程修改。'
          }
          const updated = this.applyScheduleAction(payload.schedule_action)
          return updated ? '已修改日程表' : '日程修改失败，请补充信息后重试'
        }
        if (typeof payload.reply_text === 'string' && payload.reply_text.trim()) {
          return payload.reply_text.trim()
        }
      }

      if (typeof rawReply === 'string' && rawReply.trim()) {
        return rawReply.trim()
      }
      return '后端未返回内容'
    },
    formatVoiceDuration(durationMs) {
      const seconds = Math.max(1, Math.round((Number(durationMs) || 0) / 1000))
      return `${seconds}''`
    },
    buildUserVoiceMessage(voiceSrc, transcript, durationMs = 0, extra = {}) {
      return {
        id: this.buildMessageId(),
        from: 'user',
        kind: 'voice',
        voiceSrc,
        durationLabel: this.formatVoiceDuration(durationMs),
        transcript: transcript || '',
        showTranscript: false,
        voiceStorageType: (extra && extra.voiceStorageType) || '',
        voiceStorageKey: (extra && extra.voiceStorageKey) || '',
      }
    },
    toggleVoiceTranscript(msg) {
      if (!msg || msg.kind !== 'voice' || msg.from !== 'user') return
      if (!msg.transcript) {
        uni.showToast({ title: '暂未识别到文字', icon: 'none' })
        return
      }
      msg.showTranscript = !msg.showTranscript
    },
    playMessageVoice(msg) {
      const source = (msg && msg.voiceSrc) || ''
      if (!source) {
        uni.showToast({ title: '语音文件不存在', icon: 'none' })
        return
      }
      if (this.audioContext) {
        this.audioContext.stop()
        this.audioContext.destroy()
        this.audioContext = null
      }
      const ctx = uni.createInnerAudioContext()
      this.audioContext = ctx
      ctx.autoplay = true
      ctx.src = source
      ctx.onError(() => {
        uni.showToast({ title: '语音播放失败', icon: 'none' })
      })
      ctx.play()
    },
    async onPlayAiReply(msg) {
      if (msg && msg.audioFileUrl) {
        await this.downloadAndPlayVoice(msg.audioFileUrl)
        return
      }
      uni.showToast({ title: '该回复暂无关联语音', icon: 'none' })
    },
    copyMessageText(msg) {
      const text = (msg && msg.text && String(msg.text).trim()) || ''
      if (!text) {
        uni.showToast({ title: '暂无可复制文本', icon: 'none' })
        return
      }
      uni.setClipboardData({
        data: text,
        success: () => {
          uni.showToast({ title: '已复制', icon: 'success' })
        },
        fail: () => {
          uni.showToast({ title: '复制失败', icon: 'none' })
        },
      })
    },
    openCopyTextPanel(msg) {
      const text = (msg && msg.text && String(msg.text).trim()) || ''
      if (!text) {
        uni.showToast({ title: '暂无可复制文本', icon: 'none' })
        return
      }
      this.copyTextContent = text
      this.copyTextPanelVisible = true
    },
    closeCopyTextPanel() {
      this.copyTextPanelVisible = false
    },
    copyTextContentNow() {
      if (!this.copyTextContent) {
        uni.showToast({ title: '暂无可复制文本', icon: 'none' })
        return
      }
      uni.setClipboardData({
        data: this.copyTextContent,
        success: () => {
          uni.showToast({ title: '已复制', icon: 'success' })
        },
        fail: () => {
          uni.showToast({ title: '复制失败', icon: 'none' })
        },
      })
    },
    extractErrorMessage(errorData, fallback) {
      if (!errorData) return fallback
      if (typeof errorData === 'string') return errorData
      if (typeof errorData.detail === 'string') return errorData.detail
      if (typeof errorData.message === 'string') return errorData.message
      return fallback
    },
    handleUnauthorized(message = '登录已过期，请重新登录') {
      this.authToken = ''
      this.authUsername = ''
      this.isUserLoggedIn = false
      uni.removeStorageSync(this.storageKeys.accessToken)
      uni.removeStorageSync(this.storageKeys.authUsername)
      this.openLoginDialog()
      uni.showToast({ title: message, icon: 'none' })
    },
    requestJson({ path, method = 'GET', data = null, withAuth = false }) {
      return new Promise((resolve, reject) => {
        const headers = {
          'Content-Type': 'application/json',
        }
        if (withAuth && this.authToken) {
          headers.Authorization = `Bearer ${this.authToken}`
        }

        uni.request({
          url: this.apiUrl(path),
          method,
          data,
          header: headers,
          success: (res) => {
            const ok = res.statusCode >= 200 && res.statusCode < 300
            if (ok) {
              resolve(res.data || {})
              return
            }
            if (res.statusCode === 401) {
              this.handleUnauthorized(this.extractErrorMessage(res.data, '登录已失效，请重新登录'))
            }
            reject({
              statusCode: res.statusCode,
              message: this.extractErrorMessage(res.data, `请求失败(${res.statusCode})`),
            })
          },
          fail: (err) => {
            reject({
              statusCode: 0,
              message: (err && err.errMsg) || '网络连接失败',
            })
          },
        })
      })
    },
    buildAuthHeader() {
      if (!this.authToken) {
        throw new Error('请先登录后再使用此功能')
      }
      return {
        Authorization: `Bearer ${this.authToken}`,
      }
    },
    async ensureAuthToken() {
      if (this.authToken) return this.authToken
      this.openLoginDialog()
      throw new Error('请先登录后再使用此功能')
    },
    chooseAudioFile() {
      return new Promise((resolve, reject) => {
        if (typeof uni.chooseFile === 'function') {
          uni.chooseFile({
            count: 1,
            extension: ['mp3', 'wav', 'm4a'],
            success: (res) => {
              const picked = (res.tempFiles && res.tempFiles[0]) || {}
              const filePath = picked.path || picked.tempFilePath || ''
              if (!filePath) {
                reject(new Error('未获取到音频文件路径'))
                return
              }
              resolve({
                filePath,
                fileName: picked.name || `voice_${Date.now()}.mp3`,
              })
            },
            fail: (err) => {
              reject(new Error((err && err.errMsg) || '选择音频失败'))
            },
          })
          return
        }

        reject(new Error('当前端不支持选择音频文件'))
      })
    },
    uploadVoiceWithText(filePath, fileName) {
      return new Promise((resolve, reject) => {
        uni.uploadFile({
          url: this.apiUrl(this.apiPaths.chatVoice),
          filePath,
          name: 'audio',
          header: this.buildAuthHeader(),
          formData: {
            with_text: 'true',
            with_audio: String(this.chatOptions.withAudio),
            prompt: String(this.promptIds.chatAssistant),
          },
          success: (res) => {
            if (res.statusCode < 200 || res.statusCode >= 300) {
              if (res.statusCode === 401) {
                this.handleUnauthorized('登录已失效，请重新登录')
              }
              reject(new Error(`语音上传失败(${res.statusCode})`))
              return
            }
            try {
              const parsed = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
              resolve(parsed)
            } catch (parseError) {
              reject(new Error('语音接口返回格式异常'))
            }
          },
          fail: (err) => {
            reject(new Error((err && err.errMsg) || '语音上传失败'))
          },
        })
      })
    },
    downloadAndPlayVoice(audioFileUrl) {
      return new Promise((resolve, reject) => {
        const fullUrl = /^https?:\/\//.test(audioFileUrl)
          ? audioFileUrl
          : this.apiUrl(audioFileUrl)
        uni.downloadFile({
          url: fullUrl,
          header: this.buildAuthHeader(),
          success: (res) => {
            if (res.statusCode < 200 || res.statusCode >= 300 || !res.tempFilePath) {
              if (res.statusCode === 401) {
                this.handleUnauthorized('登录已失效，请重新登录')
              }
              reject(new Error(`语音下载失败(${res.statusCode})`))
              return
            }

            if (this.audioContext) {
              this.audioContext.stop()
              this.audioContext.destroy()
              this.audioContext = null
            }

            const ctx = uni.createInnerAudioContext()
            this.audioContext = ctx
            ctx.autoplay = true
            ctx.src = res.tempFilePath
            ctx.onEnded(() => {
              resolve()
            })
            ctx.onError(() => {
              reject(new Error('语音播放失败'))
            })
            ctx.play()
          },
          fail: (err) => {
            reject(new Error((err && err.errMsg) || '语音下载失败'))
          },
        })
      })
    },
    onModuleChange(key) {
      this.currentModule = key
      this.closeCopyTextPanel()
      this.closeScheduleFieldEditor()
      if (key !== 'schedule') {
        this.closeCalendarDrawer()
      }
      if (key !== 'monitor') {
        this.closeMonitorCamera()
      }
    },
    toggleSidebar() {
      this.sidebarExpanded = !this.sidebarExpanded
    },
    async onSend() {
      if (this.chatBusy) return
      const message = this.inputText.trim()
      if (!message) return

      this.messages.push({
        id: this.buildMessageId(),
        from: 'user',
        text: message,
      })
      this.inputText = ''
      this.chatBusy = true
      this.showAiThinking = true

      try {
        await this.ensureAuthToken()
        const response = await this.requestJson({
          path: this.apiPaths.chatText,
          method: 'POST',
          data: {
            message,
            prompt: this.promptIds.chatAssistant,
            with_text: this.chatOptions.withText,
            with_audio: this.chatOptions.withAudio,
          },
          withAuth: true,
        })
        const assistantText = await this.normalizeAssistantReply(response)
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: assistantText,
          audioFileUrl: (response && response.audio_file_url) || '',
        })
      } catch (error) {
        this.messages.push({
          id: this.buildMessageId(),
          from: 'ai',
          text: `接口调用失败：${(error && error.message) || '未知错误'}`,
        })
      } finally {
        this.chatBusy = false
        this.showAiThinking = false
      }
    },
    async onPickOcrImage(source = 'album') {
      if (source === 'camera') {
        this.ocrInputMode = 'camera'
        await this.openOcrCamera()
        return
      }
      this.ocrInputMode = 'album'
      this.closeOcrCamera()
      this.pickOcrImageBySource(['album'])
    },
    async setOcrInputMode(mode) {
      this.ocrInputMode = mode
      if (mode === 'camera') {
        await this.openOcrCamera()
      } else {
        this.closeOcrCamera()
      }
    },
    onOcrDropTap() {
      if (this.ocrInputMode === 'camera') {
        if (!this.ocrCameraVisible) {
          this.openOcrCamera()
        }
        return
      }
      this.pickOcrImageBySource(['album'])
    },
    pickOcrImageBySource(sourceType) {
      if (this.ocrCapturedObjectUrl && typeof URL !== 'undefined' && URL.revokeObjectURL) {
        URL.revokeObjectURL(this.ocrCapturedObjectUrl)
        this.ocrCapturedObjectUrl = ''
      }
      this.ocrImageBlob = null
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType,
        success: (res) => {
          const filePath = (res.tempFilePaths && res.tempFilePaths[0]) || ''
          if (!filePath) return
          const pickedFile = res.tempFiles && res.tempFiles[0] && res.tempFiles[0].file
          if (pickedFile) {
            this.ocrImageBlob = pickedFile
          }
          this.ocrImageUrl = filePath
          this.ocrExplainText = ''
        },
      })
    },
    async openOcrCamera() {
      if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        this.pickOcrImageBySource(['camera'])
        return
      }

      try {
        this.stopOcrCameraStream()
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        })
        this.ocrCameraStream = stream
        this.ocrCameraVisible = true
        this.$nextTick(() => {
          const video = this.resolveOcrCameraVideoEl()
          if (video) {
            video.srcObject = stream
            if (typeof video.play === 'function') {
              video.play().catch(() => {})
            }
          }
        })
      } catch (error) {
        uni.showToast({ title: '无法打开摄像头', icon: 'none' })
      }
    },
    captureOcrPhoto() {
      const video = this.resolveOcrCameraVideoEl()
      if (!video) {
        uni.showToast({ title: '摄像头未就绪', icon: 'none' })
        return
      }

      const width = video.videoWidth || Math.max((video.clientWidth || 640), 640)
      const height = video.videoHeight || Math.max((video.clientHeight || 360), 360)
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        uni.showToast({ title: '拍照失败，请重试', icon: 'none' })
        return
      }
      ctx.drawImage(video, 0, 0, width, height)

      if (canvas.toBlob && typeof URL !== 'undefined' && URL.createObjectURL) {
        canvas.toBlob((blob) => {
          if (!blob) {
            this.ocrImageUrl = canvas.toDataURL('image/jpeg', 0.92)
            this.ocrImageBlob = this.dataUrlToBlob(this.ocrImageUrl)
          } else {
            if (this.ocrCapturedObjectUrl && URL.revokeObjectURL) {
              URL.revokeObjectURL(this.ocrCapturedObjectUrl)
            }
            this.ocrCapturedObjectUrl = URL.createObjectURL(blob)
            this.ocrImageUrl = this.ocrCapturedObjectUrl
            this.ocrImageBlob = blob
          }
          this.ocrExplainText = ''
          this.closeOcrCamera()
        }, 'image/jpeg', 0.92)
        return
      }

      this.ocrImageUrl = canvas.toDataURL('image/jpeg', 0.92)
      this.ocrImageBlob = this.dataUrlToBlob(this.ocrImageUrl)
      this.ocrExplainText = ''
      this.closeOcrCamera()
    },
    dataUrlToBlob(dataUrl) {
      if (!dataUrl || typeof dataUrl !== 'string' || dataUrl.indexOf(',') < 0) return null
      const segments = dataUrl.split(',')
      const header = segments[0] || ''
      const body = segments[1] || ''
      const mimeMatch = header.match(/data:(.*?);base64/)
      const mime = (mimeMatch && mimeMatch[1]) || 'image/jpeg'
      const binary = atob(body)
      const len = binary.length
      const array = new Uint8Array(len)
      for (let i = 0; i < len; i += 1) {
        array[i] = binary.charCodeAt(i)
      }
      return new Blob([array], { type: mime })
    },
    uploadOcrImageByPath(filePath, withAudio = false) {
      return new Promise((resolve, reject) => {
        uni.uploadFile({
          url: this.apiUrl(this.apiPaths.ocrAnalyze),
          filePath,
          name: 'images',
          timeout: this.ocrRequestTimeoutMs,
          formData: {
            prompt: '',
            with_audio: String(withAudio),
          },
          header: this.buildAuthHeader(),
          success: (res) => {
            if (res.statusCode < 200 || res.statusCode >= 300) {
              if (res.statusCode === 401) {
                this.handleUnauthorized('登录已失效，请重新登录')
              }
              reject(new Error(`OCR识别失败(${res.statusCode})`))
              return
            }
            try {
              const parsed = typeof res.data === 'string' ? JSON.parse(res.data) : (res.data || {})
              resolve(parsed)
            } catch (error) {
              reject(new Error('OCR接口返回格式异常'))
            }
          },
          fail: (err) => {
            reject(new Error((err && err.errMsg) || 'OCR上传失败'))
          },
        })
      })
    },
    uploadOcrImageByBlob(blob, withAudio = false) {
      return new Promise((resolve, reject) => {
        if (!blob || typeof FormData === 'undefined' || typeof fetch === 'undefined') {
          reject(new Error('当前环境不支持该图片上传方式'))
          return
        }

        const canAbort = typeof AbortController !== 'undefined'
        const controller = canAbort ? new AbortController() : null
        const timer = setTimeout(() => {
          if (controller) {
            controller.abort()
          }
        }, this.ocrRequestTimeoutMs)

        const formData = new FormData()
        formData.append('images', blob, `ocr_${Date.now()}.jpg`)
        formData.append('prompt', '')
        formData.append('with_audio', String(withAudio))
        fetch(this.apiUrl(this.apiPaths.ocrAnalyze), {
          method: 'POST',
          headers: this.buildAuthHeader(),
          body: formData,
          signal: controller ? controller.signal : undefined,
        })
          .then(async (res) => {
            clearTimeout(timer)
            if (!res.ok) {
              if (res.status === 401) {
                this.handleUnauthorized('登录已失效，请重新登录')
              }
              reject(new Error(`OCR识别失败(${res.status})`))
              return
            }
            try {
              const json = await res.json()
              resolve(json || {})
            } catch (error) {
              reject(new Error('OCR接口返回格式异常'))
            }
          })
          .catch((error) => {
            clearTimeout(timer)
            const aborted = error && error.name === 'AbortError'
            reject(new Error(aborted ? 'OCR识别超时（5分钟）' : ((error && error.message) || 'OCR上传失败')))
          })
      })
    },
    async submitOcrAnalyze(withAudio = false) {
      if (this.ocrSubmitting) return
      if (!this.ocrImageUrl) {
        uni.showToast({ title: '请先选择图片', icon: 'none' })
        return
      }

      this.ocrSubmitting = true
      this.ocrExplainText = '正在上传并识别，请稍候...'
      try {
        await this.ensureAuthToken()
        const hasBlobUpload = !!this.ocrImageBlob
        const result = hasBlobUpload
          ? await this.uploadOcrImageByBlob(this.ocrImageBlob, withAudio)
          : await this.uploadOcrImageByPath(this.ocrImageUrl, withAudio)

        const text = (result && result.text) || ''
        const audioFileUrl = (result && result.audio_file_url) || ''
        this.ocrExplainText = text || 'OCR接口未返回可展示文本'

        if (withAudio && audioFileUrl) {
          await this.downloadAndPlayVoice(audioFileUrl)
        }
      } catch (error) {
        this.ocrExplainText = ''
        uni.showToast({ title: (error && error.message) || 'OCR识别失败', icon: 'none' })
      } finally {
        this.ocrSubmitting = false
      }
    },
    closeOcrCamera() {
      this.ocrCameraVisible = false
      this.stopOcrCameraStream()
    },
    stopOcrCameraStream() {
      if (this.ocrCameraStream) {
        this.ocrCameraStream.getTracks().forEach((track) => track.stop())
        this.ocrCameraStream = null
      }
      const video = this.resolveOcrCameraVideoEl()
      if (video && video.srcObject) {
        video.srcObject = null
      }
    },
    resolveOcrCameraVideoEl() {
      let video = this.$refs.ocrCameraVideo
      if (Array.isArray(video)) {
        video = video[0]
      }
      if (video && video.$el) {
        if (typeof video.$el.querySelector === 'function') {
          video = video.$el.querySelector('video') || video.$el
        } else {
          video = video.$el
        }
      }
      return video || null
    },
    async toggleMonitorCamera() {
      if (this.monitorCameraVisible) {
        this.closeMonitorCamera()
        return
      }
      await this.openMonitorCamera()
    },
    async openMonitorCamera() {
      if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        uni.showToast({ title: '当前环境不支持摄像头预览', icon: 'none' })
        return
      }
      try {
        this.stopMonitorCameraStream()
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        })
        this.monitorCameraStream = stream
        this.monitorCameraVisible = true
        this.$nextTick(() => {
          const video = this.resolveMonitorCameraVideoEl()
          if (video) {
            video.srcObject = stream
            if (typeof video.play === 'function') {
              video.play().catch(() => {})
            }
          }
        })
      } catch (error) {
        this.monitorCameraVisible = false
        uni.showToast({ title: '无法打开摄像头', icon: 'none' })
      }
    },
    closeMonitorCamera() {
      this.monitorCameraVisible = false
      this.stopMonitorDetectionLoop()
      this.monitorDetecting = false
      this.monitorStatusHint = '点击“打开摄像头”后可开始检测。'
      this.stopMonitorCameraStream()
    },
    stopMonitorCameraStream() {
      if (this.monitorCameraStream) {
        this.monitorCameraStream.getTracks().forEach((track) => track.stop())
        this.monitorCameraStream = null
      }
      const video = this.resolveMonitorCameraVideoEl()
      if (video && video.srcObject) {
        video.srcObject = null
      }
    },
    resolveMonitorCameraVideoEl() {
      let video = this.$refs.monitorCameraVideo
      if (Array.isArray(video)) {
        video = video[0]
      }
      if (video && video.$el) {
        if (typeof video.$el.querySelector === 'function') {
          video = video.$el.querySelector('video') || video.$el
        } else {
          video = video.$el
        }
      }
      return video || null
    },
    async toggleMonitorDetecting() {
      if (!this.monitorCameraVisible) {
        uni.showToast({ title: '请先打开摄像头', icon: 'none' })
        return
      }
      if (this.monitorDetecting) {
        this.stopMonitorDetectionLoop()
        this.monitorDetecting = false
        this.monitorStatusHint = '检测已停止，可重新开始。'
        return
      }

      try {
        await this.ensureAuthToken()
      } catch (error) {
        this.monitorStatusHint = (error && error.message) || '请先登录后再使用监控检测'
        return
      }

      this.monitorDetecting = true
      this.monitorStatusHint = '检测中：正在调用 YOLO 跌倒识别服务...'
      this.scheduleMonitorDetectionTick(0)
    },
    stopMonitorDetectionLoop() {
      if (this.monitorDetectionTimer) {
        clearTimeout(this.monitorDetectionTimer)
        this.monitorDetectionTimer = null
      }
      this.monitorRequesting = false
    },
    scheduleMonitorDetectionTick(delay = 600) {
      if (!this.monitorDetecting) return
      if (this.monitorDetectionTimer) {
        clearTimeout(this.monitorDetectionTimer)
      }
      this.monitorDetectionTimer = setTimeout(async () => {
        await this.runMonitorDetectionOnce()
        this.scheduleMonitorDetectionTick(650)
      }, delay)
    },
    async runMonitorDetectionOnce() {
      if (!this.monitorDetecting || this.monitorRequesting || !this.monitorCameraVisible) return
      this.monitorRequesting = true
      try {
        const frameBlob = await this.captureMonitorFrameBlob()
        if (!frameBlob) {
          this.monitorStatusHint = '摄像头尚未准备好，正在等待画面...'
          return
        }
        const result = await this.requestMonitorFallDetect(frameBlob)
        const hasFall = !!(result && result.has_fall)
        const condition = (result && result.condition) || ''
        const personCount = Number((result && result.person_count) || 0)
        this.monitorLastResult = {
          hasFall,
          condition,
          personCount,
        }
        if (hasFall) {
          this.monitorStatusHint = `检测到疑似跌倒${condition ? `（${condition}）` : ''}，请及时确认。`
        } else {
          this.monitorStatusHint = `检测中：当前未发现跌倒（画面人数：${personCount}）。`
        }
        
        if (result && result.persons) {
          this.drawYoloBoxes(result.persons)
        } else {
          this.drawYoloBoxes([])
        }
      } catch (error) {
        this.monitorStatusHint = `检测服务异常：${(error && error.message) || '无法连接 YOLO 服务'}`
      } finally {
        this.monitorRequesting = false
      }
    },
    drawYoloBoxes(persons) {
      const videoEl = this.resolveMonitorCameraVideoEl()
      if (!videoEl) return

      const renderWidth = videoEl.clientWidth || videoEl.offsetWidth || 0
      const renderHeight = videoEl.clientHeight || videoEl.offsetHeight || 0
      const videoWidth = videoEl.videoWidth || 0
      const videoHeight = videoEl.videoHeight || 0
      if (!renderWidth || !renderHeight || !videoWidth || !videoHeight) return

      const scale = Math.max(renderWidth / videoWidth, renderHeight / videoHeight)
      const offsetX = (renderWidth - videoWidth * scale) / 2
      const offsetY = (renderHeight - videoHeight * scale) / 2
      const safePersons = Array.isArray(persons) ? persons : []

      const canvasEl = typeof document !== 'undefined' ? document.getElementById('yoloCanvas') : null
      if (canvasEl && typeof canvasEl.getContext === 'function') {
        const dpr = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1
        const targetWidth = Math.max(1, Math.round(renderWidth * dpr))
        const targetHeight = Math.max(1, Math.round(renderHeight * dpr))
        if (canvasEl.width !== targetWidth) {
          canvasEl.width = targetWidth
        }
        if (canvasEl.height !== targetHeight) {
          canvasEl.height = targetHeight
        }

        const ctx = canvasEl.getContext('2d')
        if (!ctx) return

        ctx.setTransform(1, 0, 0, 1, 0, 0)
        ctx.clearRect(0, 0, canvasEl.width, canvasEl.height)
        ctx.scale(dpr, dpr)

        safePersons.forEach((person) => {
          const bbox = person && person.bbox
          if (!Array.isArray(bbox) || bbox.length < 4) return

          const [x1, y1, x2, y2] = bbox
          const x = x1 * scale + offsetX
          const y = y1 * scale + offsetY
          const w = (x2 - x1) * scale
          const h = (y2 - y1) * scale

          ctx.strokeStyle = person.is_fall ? 'red' : 'green'
          ctx.lineWidth = 3
          ctx.strokeRect(x, y, w, h)

          ctx.fillStyle = person.is_fall ? 'red' : 'green'
          ctx.font = '16px sans-serif'
          ctx.fillText(`${person.status || 'Normal'}`, x, y > 20 ? y - 5 : y + 15)
        })
        return
      }

      const ctx = uni.createCanvasContext('yoloCanvas', this)
      ctx.clearRect(0, 0, renderWidth, renderHeight)
      safePersons.forEach((person) => {
        const bbox = person && person.bbox
        if (!Array.isArray(bbox) || bbox.length < 4) return

        const [x1, y1, x2, y2] = bbox
        const x = x1 * scale + offsetX
        const y = y1 * scale + offsetY
        const w = (x2 - x1) * scale
        const h = (y2 - y1) * scale

        ctx.setStrokeStyle(person.is_fall ? 'red' : 'green')
        ctx.setLineWidth(3)
        ctx.strokeRect(x, y, w, h)

        ctx.setFillStyle(person.is_fall ? 'red' : 'green')
        ctx.setFontSize(16)
        ctx.fillText(`${person.status || 'Normal'}`, x, y > 20 ? y - 5 : y + 15)
      })
      ctx.draw()
    },
    captureMonitorFrameBlob() {
      return new Promise((resolve) => {
        const video = this.resolveMonitorCameraVideoEl()
        if (!video) {
          resolve(null)
          return
        }
        const width = video.videoWidth || 0
        const height = video.videoHeight || 0
        if (!width || !height) {
          resolve(null)
          return
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          resolve(null)
          return
        }
        ctx.drawImage(video, 0, 0, width, height)
        if (typeof canvas.toBlob === 'function') {
          canvas.toBlob((blob) => resolve(blob || null), 'image/jpeg', 0.88)
          return
        }
        const dataUrl = canvas.toDataURL('image/jpeg', 0.88)
        resolve(this.dataUrlToBlob(dataUrl))
      })
    },
    requestMonitorFallDetect(frameBlob) {
      return new Promise((resolve, reject) => {
        if (!frameBlob || typeof FormData === 'undefined' || typeof fetch === 'undefined') {
          reject(new Error('当前环境不支持监控检测上传'))
          return
        }
        const formData = new FormData()
        formData.append('image', frameBlob, `monitor_${Date.now()}.jpg`)

        const headers = {}
        if (this.authToken) {
          headers.Authorization = `Bearer ${this.authToken}`
        }

        fetch(this.monitorApiUrl(this.apiPaths.monitorDetectFrame), {
          method: 'POST',
          headers,
          body: formData,
        })
          .then(async (res) => {
            if (!res.ok) {
              reject(new Error(`YOLO 服务不可用(${res.status})`))
              return
            }
            try {
              const json = await res.json()
              resolve(json || {})
            } catch (error) {
              reject(new Error('YOLO 返回格式异常'))
            }
          })
          .catch((error) => {
            reject(new Error((error && error.message) || '无法连接 YOLO 服务'))
          })
      })
    },
    getChatHistoryStorageKey() {
      const username = ((this.authUsername || '').trim().toLowerCase()) || 'guest'
      return `${this.storageKeys.chatHistoryPrefix}${username}`
    },
    schedulePersistChatHistory() {
      if (this.chatPersistTimer) {
        clearTimeout(this.chatPersistTimer)
      }
      this.chatPersistTimer = setTimeout(() => {
        this.flushPersistChatHistory()
      }, 180)
    },
    flushPersistChatHistory() {
      const maxMessages = Number((this.chatHistoryOptions && this.chatHistoryOptions.maxMessages) || 80)
      const sliced = Array.isArray(this.messages)
        ? this.messages.slice(-Math.max(1, maxMessages))
        : []

      const payload = sliced.map((msg) => ({
        id: msg.id,
        from: msg.from,
        kind: msg.kind || 'text',
        text: msg.text || '',
        durationLabel: msg.durationLabel || '',
        transcript: msg.transcript || '',
        showTranscript: !!msg.showTranscript,
        audioFileUrl: msg.audioFileUrl || '',
        voiceSrc: msg.voiceSrc || '',
        voiceStorageType: msg.voiceStorageType || '',
        voiceStorageKey: msg.voiceStorageKey || '',
      }))
      uni.setStorageSync(this.getChatHistoryStorageKey(), payload)
    },
    async restoreChatHistory() {
      const key = this.getChatHistoryStorageKey()
      const saved = uni.getStorageSync(key)
      if (!Array.isArray(saved) || !saved.length) {
        this.messages = [{ id: 1, from: 'ai', text: '您好，我是康复小助手，很高兴为您服务。' }]
        return
      }

      const restored = []
      for (const item of saved) {
        const msg = {
          id: item.id || this.buildMessageId(),
          from: item.from || 'ai',
          kind: item.kind || 'text',
          text: item.text || '',
          durationLabel: item.durationLabel || '',
          transcript: item.transcript || '',
          showTranscript: !!item.showTranscript,
          audioFileUrl: item.audioFileUrl || '',
          voiceSrc: item.voiceSrc || '',
          voiceStorageType: item.voiceStorageType || '',
          voiceStorageKey: item.voiceStorageKey || '',
        }

        if (msg.kind === 'voice' && msg.voiceStorageType === 'idb' && msg.voiceStorageKey) {
          try {
            const blob = await this.getVoiceBlobFromDb(msg.voiceStorageKey)
            if (blob && typeof URL !== 'undefined' && URL.createObjectURL) {
              msg.voiceSrc = URL.createObjectURL(blob)
              this.voiceObjectUrls.push(msg.voiceSrc)
            }
          } catch (error) {
          }
        }
        restored.push(msg)
      }
      this.messages = restored.length
        ? restored
        : [{ id: 1, from: 'ai', text: '您好，我是康复小助手，很高兴为您服务。' }]
    },
    saveVoiceFileToPersistentPath(filePath) {
      return new Promise((resolve) => {
        if (!filePath || typeof uni.saveFile !== 'function') {
          resolve('')
          return
        }
        uni.saveFile({
          tempFilePath: filePath,
          success: (res) => resolve((res && res.savedFilePath) || ''),
          fail: () => resolve(''),
        })
      })
    },
    openVoiceDb() {
      return new Promise((resolve, reject) => {
        if (this.voiceDb) {
          resolve(this.voiceDb)
          return
        }
        if (typeof indexedDB === 'undefined') {
          reject(new Error('当前环境不支持 IndexedDB'))
          return
        }
        const request = indexedDB.open(this.storageKeys.voiceDbName, 1)
        request.onupgradeneeded = () => {
          const db = request.result
          if (!db.objectStoreNames.contains(this.storageKeys.voiceDbStore)) {
            db.createObjectStore(this.storageKeys.voiceDbStore)
          }
        }
        request.onsuccess = () => {
          this.voiceDb = request.result
          resolve(this.voiceDb)
        }
        request.onerror = () => {
          reject(new Error('语音本地库初始化失败'))
        }
      })
    },
    async putVoiceBlobToDb(key, blob) {
      const db = await this.openVoiceDb()
      return new Promise((resolve, reject) => {
        const tx = db.transaction([this.storageKeys.voiceDbStore], 'readwrite')
        const store = tx.objectStore(this.storageKeys.voiceDbStore)
        const req = store.put(blob, key)
        req.onsuccess = () => resolve(true)
        req.onerror = () => reject(new Error('语音本地保存失败'))
      })
    },
    async getVoiceBlobFromDb(key) {
      const db = await this.openVoiceDb()
      return new Promise((resolve, reject) => {
        const tx = db.transaction([this.storageKeys.voiceDbStore], 'readonly')
        const store = tx.objectStore(this.storageKeys.voiceDbStore)
        const req = store.get(key)
        req.onsuccess = () => resolve(req.result || null)
        req.onerror = () => reject(new Error('语音本地读取失败'))
      })
    },
    setWeeklyManualScore(questionId, score) {
      this.weeklyManualForm.scores[questionId] = score
    },
    switchWeeklyPage(pageIndex) {
      if (pageIndex < 0 || pageIndex >= this.weeklyQuestionnairePages.length) return
      this.activeWeeklyPageIndex = pageIndex
    },
    goPrevWeeklyPage() {
      this.switchWeeklyPage(this.activeWeeklyPageIndex - 1)
    },
    goNextWeeklyPage() {
      this.switchWeeklyPage(this.activeWeeklyPageIndex + 1)
    },
    /**
     * Load monthly medication cache from local storage.
     * @returns {void}
     */
    loadMedicationMonthCacheFromStorage() {
      const saved = uni.getStorageSync(this.medicationMonthCacheStorageKey)
      if (!saved || typeof saved !== 'object') {
        this.medicationMonthCache = {}
        return
      }

      const nextCache = {}
      Object.keys(saved).forEach((cacheKey) => {
        nextCache[cacheKey] = this.cloneMedicationMonthData(saved[cacheKey])
      })
      this.medicationMonthCache = nextCache
    },
    /**
     * Persist monthly medication cache to local storage.
     * @returns {void}
     */
    persistMedicationMonthCacheToStorage() {
      uni.setStorageSync(this.medicationMonthCacheStorageKey, this.medicationMonthCache)
    },
    /**
     * Build daily storage key for reminder de-duplication state.
     * @param {string} dateKey - Date text in YYYY-MM-DD format.
     * @returns {string} Storage key.
     */
    getMedicationReminderDailyStorageKey(dateKey) {
      return `${this.medicationReminderStoragePrefix}${dateKey}`
    },
    /**
     * Build cache key for monthly medication records.
     * @param {number} year - Calendar year.
     * @param {number} month - Calendar month index in range [0, 11].
     * @returns {string} Stable key formatted as YYYY-MM.
     */
    getMedicationMonthCacheKey(year, month) {
      return `${year}-${String(month + 1).padStart(2, '0')}`
    },
    /**
     * Clone monthly medication data to avoid cross-reference side effects.
     * @param {{statusMap?: Object, recordsMap?: Object}} monthData - Raw month payload.
     * @returns {{statusMap: Object, recordsMap: Object}} Deep-cloned month payload.
     */
    cloneMedicationMonthData(monthData = {}) {
      const statusMap = { ...(monthData.statusMap || {}) }
      const sourceRecordsMap = monthData.recordsMap || {}
      const recordsMap = {}
      Object.keys(sourceRecordsMap).forEach((day) => {
        const records = Array.isArray(sourceRecordsMap[day]) ? sourceRecordsMap[day] : []
        recordsMap[day] = records.map((record) => ({ ...record }))
      })
      return { statusMap, recordsMap }
    },
    /**
     * Get month data from cache and lazily initialize fallback mock data when missing.
     * @param {number} year - Calendar year.
     * @param {number} month - Calendar month index in range [0, 11].
     * @returns {{statusMap: Object, recordsMap: Object}} Cloned month data snapshot.
     */
    getMedicationMonthDataSnapshot(year, month) {
      const cacheKey = this.getMedicationMonthCacheKey(year, month)
      if (!this.medicationMonthCache[cacheKey]) {
        this.medicationMonthCache[cacheKey] = this.cloneMedicationMonthData(
          this.getMedicationMonthData(year, month)
        )
      }
      return this.cloneMedicationMonthData(this.medicationMonthCache[cacheKey])
    },
    /**
     * Persist current in-memory month state back to month cache.
     * @returns {void}
     */
    persistCurrentMonthDataToCache() {
      const cacheKey = this.getMedicationMonthCacheKey(this.currentCalendarYear, this.currentCalendarMonth)
      this.medicationMonthCache[cacheKey] = this.cloneMedicationMonthData({
        statusMap: this.medicationStatusMap,
        recordsMap: this.medicationRecordsMap,
      })
      this.persistMedicationMonthCacheToStorage()
    },
    /**
     * Check whether a calendar day is in the future compared with local today.
     * @param {number} year - Calendar year.
     * @param {number} month - Calendar month index in range [0, 11].
     * @param {number} day - Day of month in range [1, 31].
     * @returns {boolean} True if target day is after today.
     */
    isFutureDay(year, month, day) {
      const today = new Date()
      const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())
      const target = new Date(year, month, day)
      return target.getTime() > todayStart.getTime()
    },
    /**
     * Rebuild calendar cell list based on current month maps.
     * @returns {void}
     */
    rebuildMedicationCalendarCells() {
      const year = this.currentCalendarYear
      const month = this.currentCalendarMonth
      const firstDay = new Date(year, month, 1).getDay()
      const offset = firstDay === 0 ? 6 : firstDay - 1
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      const cells = []

      for (let i = 0; i < offset; i += 1) {
        cells.push({ day: 0, taken: null, isUnrecorded: false })
      }
      for (let day = 1; day <= daysInMonth; day += 1) {
        cells.push({
          day,
          taken: !!this.medicationStatusMap[day],
          isUnrecorded: this.isFutureDay(year, month, day),
        })
      }
      while (cells.length % 7 !== 0) {
        cells.push({ day: 0, taken: null, isUnrecorded: false })
      }
      this.medicationCalendarCells = cells
    },
    /**
     * Update one day status by records and keep month cache in sync.
     * @param {number} day - Day of month in range [1, 31].
     * @param {Array<Object>} records - Medication records for that day.
     * @returns {void}
     */
    updateDayMedicationStatus(day, records = []) {
      if (!day) return
      const safeRecords = Array.isArray(records) ? records : []
      this.medicationStatusMap[day] = safeRecords.length ? safeRecords.every((item) => !!item.taken) : false
    },
    /**
     * Convert HH:mm to minutes from start of day.
     * @param {string} timeText - Time string in HH:mm format.
     * @returns {number} Minutes value or -1 when format invalid.
     */
    parseTimeToMinutes(timeText) {
      if (!timeText || typeof timeText !== 'string') return -1
      const match = timeText.trim().match(/^(\d{2}):(\d{2})$/)
      if (!match) return -1
      const hour = Number(match[1])
      const minute = Number(match[2])
      if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return -1
      return hour * 60 + minute
    },
    /**
     * Build date key in YYYY-MM-DD format.
     * @param {Date} dateObj - Date instance.
     * @returns {string} Date key.
     */
    buildDateKey(dateObj) {
      const year = dateObj.getFullYear()
      const month = String(dateObj.getMonth() + 1).padStart(2, '0')
      const day = String(dateObj.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    },
    /**
     * Collect medication reminder slots for a target date.
     * @param {Date} dateObj - Target date.
     * @returns {Array<{time: string, minutes: number, taken: boolean}>} Sorted slot list.
     */
    getMedicationReminderSlots(dateObj) {
      const year = dateObj.getFullYear()
      const month = dateObj.getMonth()
      const day = dateObj.getDate()
      const monthData = this.getMedicationMonthDataSnapshot(year, month)
      const dayRecords = Array.isArray(monthData.recordsMap[day]) ? monthData.recordsMap[day] : []
      const recordMap = dayRecords.reduce((acc, record) => {
        if (record && record.time) {
          acc[record.time] = record
        }
        return acc
      }, {})

      const scheduleTimes = this.scheduleItems.map((item) => item.time).filter(Boolean)
      const recordTimes = dayRecords.map((item) => item.time).filter(Boolean)
      const uniqueTimes = Array.from(new Set(scheduleTimes.concat(recordTimes)))

      return uniqueTimes
        .map((time) => {
          const minutes = this.parseTimeToMinutes(time)
          const record = recordMap[time]
          return {
            time,
            minutes,
            taken: record ? !!record.taken : false,
          }
        })
        .filter((item) => item.minutes >= 0)
        .sort((a, b) => a.minutes - b.minutes)
    },
    /**
     * Update top status hint based on today's pending medication slots.
     * @param {Date} now - Current local date-time.
     * @returns {void}
     */
    updateMedicationStatusHint(now = new Date()) {
      const slots = this.getMedicationReminderSlots(now)
      if (!slots.length) {
        this.medicationStatus = '今日暂无服药计划'
        return
      }
      const nowMinutes = now.getHours() * 60 + now.getMinutes()
      const pendingSlots = slots.filter((slot) => !slot.taken)
      const nextPending = pendingSlots.find((slot) => slot.minutes >= nowMinutes)

      if (nextPending) {
        this.medicationStatus = `下一次用药在 ${nextPending.time}`
        return
      }
      if (pendingSlots.length) {
        this.medicationStatus = '今日仍有未服药记录'
        return
      }
      this.medicationStatus = '今日服药已完成'
    },
    /**
     * Stop and destroy reminder ringtone context if it exists.
     * @returns {void}
     */
    stopMedicationReminderSound() {
      const reminderContext = this.medicationReminderAudioContext
      if (!reminderContext) {
        return
      }
      this.medicationReminderAudioContext = null
      try {
        reminderContext.stop()
      } catch (error) {
      }
      try {
        reminderContext.destroy()
      } catch (error) {
      }
    },
    /**
     * Play medication reminder ringtone once from the sound directory.
     * @returns {void}
     */
    playMedicationReminderSound() {
      if (!this.medicationReminderSoundEnabled) {
        return
      }
      if (typeof uni.createInnerAudioContext !== 'function') {
        return
      }

      this.stopMedicationReminderSound()

      const reminderContext = uni.createInnerAudioContext()
      this.medicationReminderAudioContext = reminderContext
      reminderContext.autoplay = false
      reminderContext.src = this.medicationReminderSoundSrc

      reminderContext.onEnded(() => {
        if (this.medicationReminderAudioContext === reminderContext) {
          this.medicationReminderAudioContext = null
        }
        try {
          reminderContext.destroy()
        } catch (error) {
        }
      })

      reminderContext.onError(() => {
        if (this.medicationReminderAudioContext === reminderContext) {
          this.medicationReminderAudioContext = null
        }
        try {
          reminderContext.destroy()
        } catch (error) {
        }
      })

      try {
        reminderContext.play()
      } catch (error) {
        if (this.medicationReminderAudioContext === reminderContext) {
          this.medicationReminderAudioContext = null
        }
        try {
          reminderContext.destroy()
        } catch (destroyError) {
        }
      }
    },
    /**
     * Show alarm notification when a medication slot reaches trigger minute.
     * @param {string} timeText - Triggered medication time in HH:mm.
     * @returns {void}
     */
    triggerMedicationAlarm(timeText) {
      this.playMedicationReminderSound()
      if (typeof uni.vibrateShort === 'function') {
        try {
          uni.vibrateShort()
        } catch (error) {
        }
      }
      if (typeof uni.showModal === 'function') {
        uni.showModal({
          title: '服药提醒',
          content: `现在是 ${timeText}，请按时服药。`,
          showCancel: false,
        })
        return
      }
      uni.showToast({ title: `服药提醒 ${timeText}`, icon: 'none' })
    },
    /**
     * Execute one reminder tick, avoid duplicate alarms in same day and minute.
     * @returns {void}
     */
    runMedicationReminderCheck() {
      const now = new Date()
      const dateKey = this.buildDateKey(now)
      if (this.medicationReminderDateKey !== dateKey) {
        this.medicationReminderDateKey = dateKey
        const savedReminderMap = uni.getStorageSync(this.getMedicationReminderDailyStorageKey(dateKey))
        this.medicationReminderShownMap =
          savedReminderMap && typeof savedReminderMap === 'object'
            ? { ...savedReminderMap }
            : {}
      }

      const minuteText = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
      const minuteKey = `${dateKey} ${minuteText}`
      if (this.medicationReminderLastMinuteKey === minuteKey) {
        return
      }
      this.medicationReminderLastMinuteKey = minuteKey

      const slots = this.getMedicationReminderSlots(now)
      const matched = slots.find((slot) => slot.time === minuteText && !slot.taken)
      if (matched) {
        const alarmKey = `${dateKey}_${matched.time}`
        if (!this.medicationReminderShownMap[alarmKey]) {
          this.medicationReminderShownMap[alarmKey] = true
          uni.setStorageSync(
            this.getMedicationReminderDailyStorageKey(dateKey),
            this.medicationReminderShownMap
          )
          this.triggerMedicationAlarm(matched.time)
        }
      }

      this.updateMedicationStatusHint(now)
    },
    /**
     * Start medication reminder loop while current page is active.
     * @returns {void}
     */
    startMedicationReminderLoop() {
      this.stopMedicationReminderLoop()
      this.runMedicationReminderCheck()
      this.medicationReminderTimer = setInterval(() => {
        this.runMedicationReminderCheck()
      }, 15000)
    },
    /**
     * Stop medication reminder loop.
     * @returns {void}
     */
    stopMedicationReminderLoop() {
      if (this.medicationReminderTimer) {
        clearInterval(this.medicationReminderTimer)
        this.medicationReminderTimer = null
      }
      this.stopMedicationReminderSound()
    },
    buildMedicationCalendar(options = {}) {
      const skipScheduleFocus = !!options.skipScheduleFocus
      const year = this.currentCalendarYear
      const month = this.currentCalendarMonth
      this.calendarMonthLabel = `${year}年${String(month + 1).padStart(2, '0')}月`
      const monthData = this.getMedicationMonthDataSnapshot(year, month)
      this.medicationStatusMap = monthData.statusMap
      this.medicationRecordsMap = monthData.recordsMap
      this.rebuildMedicationCalendarCells()
      const today = new Date()
      const isCurrentMonth =
        year === today.getFullYear() &&
        month === today.getMonth()
      const defaultDay = isCurrentMonth ? today.getDate() : 1

      this.selectedCalendarDay = defaultDay
      this.selectedCalendarDetail = this.buildSelectedDayDetail(defaultDay)
      const records = this.selectedCalendarDetail.records || []
      const targetRecord = records.find((record) => !record.taken) || records[0]
      if (!skipScheduleFocus && targetRecord && targetRecord.time) {
        this.focusScheduleByTime(targetRecord.time)
      }
      this.updateMedicationStatusHint()
    },
    goPrevMonth() {
      const target = new Date(this.currentCalendarYear, this.currentCalendarMonth - 1, 1)
      this.currentCalendarYear = target.getFullYear()
      this.currentCalendarMonth = target.getMonth()
      this.buildMedicationCalendar()
    },
    goCurrentMonth() {
      const today = new Date()
      this.currentCalendarYear = today.getFullYear()
      this.currentCalendarMonth = today.getMonth()
      this.buildMedicationCalendar()
    },
    goPrevYear() {
      this.currentCalendarYear -= 1
      this.buildMedicationCalendar()
    },
    goNextYear() {
      this.currentCalendarYear += 1
      this.buildMedicationCalendar()
    },
    selectCalendarMonth(monthIndex) {
      this.currentCalendarMonth = monthIndex
      this.buildMedicationCalendar({ skipScheduleFocus: true })
      this.openCalendarDrawer()
    },
    openCalendarDrawer() {
      this.calendarDrawerVisible = true
    },
    closeCalendarDrawer() {
      this.calendarDrawerVisible = false
    },
    onCalendarDayTap(cell) {
      if (!cell.day) return
      this.selectedCalendarDay = cell.day
      this.selectedCalendarDetail = this.buildSelectedDayDetail(cell.day)
      const records = this.selectedCalendarDetail.records || []
      const targetRecord = records.find((record) => !record.taken) || records[0]
      if (targetRecord && targetRecord.time) {
        this.focusScheduleByTime(targetRecord.time)
      }
    },
    openScheduleFieldEditor(item, field) {
      if (!item || !field) return
      const labelMap = {
        time: '时间',
        medicine: '用药情况',
        bp: '血压',
        weight: '体重',
        symptom: '症状',
        mood: '心情',
        matter: '事宜',
      }
      this.scheduleEditField = field
      this.scheduleEditLabel = labelMap[field] || '内容'
      this.scheduleEditTime = item.time || ''
      this.scheduleEditValue = String(item[field] || '').replace(/^—$/, '')
      this.scheduleEditDialogVisible = true
    },
    closeScheduleFieldEditor() {
      this.scheduleEditDialogVisible = false
      this.scheduleEditField = ''
      this.scheduleEditLabel = ''
      this.scheduleEditTime = ''
      this.scheduleEditValue = ''
    },
    confirmScheduleFieldEdit() {
      const time = this.scheduleEditTime
      const field = this.scheduleEditField
      const day = this.selectedCalendarDay
      if (!time || !field) {
        this.closeScheduleFieldEditor()
        return
      }

      const value = (this.scheduleEditValue || '').trim()

      if (field === 'time') {
        const nextTime = value
        const timeReg = /^([01]\d|2[0-3]):([0-5]\d)$/
        if (!timeReg.test(nextTime)) {
          uni.showToast({ title: '时间格式应为 HH:mm', icon: 'none' })
          return
        }
        const dup = this.scheduleItems.find((item) => item.time === nextTime && item.time !== time)
        if (dup) {
          uni.showToast({ title: '该时间已存在，请更换', icon: 'none' })
          return
        }

        const idx = this.scheduleItems.findIndex((item) => item.time === time)
        if (idx >= 0) {
          this.scheduleItems[idx] = {
            ...this.scheduleItems[idx],
            time: nextTime,
          }
          this.scheduleItems.sort((a, b) => String(a.time).localeCompare(String(b.time)))
        }

        const dayRecords = Array.isArray(this.medicationRecordsMap[day])
          ? this.medicationRecordsMap[day].map((record) => ({ ...record }))
          : []
        const recordIndex = dayRecords.findIndex((record) => record.time === time)
        if (recordIndex >= 0) {
          dayRecords[recordIndex].time = nextTime
          dayRecords.sort((a, b) => String(a.time).localeCompare(String(b.time)))
          this.medicationRecordsMap[day] = dayRecords
          this.selectedCalendarDetail = this.buildSelectedDayDetail(day)
          this.updateDayMedicationStatus(day, dayRecords)
        }

        this.persistCurrentMonthDataToCache()
        this.rebuildMedicationCalendarCells()
        this.updateMedicationStatusHint()

        this.closeScheduleFieldEditor()
        this.focusScheduleByTime(nextTime)
        uni.showToast({ title: '已更新时间', icon: 'success' })
        return
      }

      const normalized = value || (field === 'matter' ? '待补充' : '—')
      const idx = this.scheduleItems.findIndex((item) => item.time === time)
      if (idx >= 0) {
        this.scheduleItems[idx] = {
          ...this.scheduleItems[idx],
          [field]: normalized,
        }
      }

      const dayRecords = Array.isArray(this.medicationRecordsMap[day])
        ? this.medicationRecordsMap[day].map((record) => ({ ...record }))
        : []
      let recordIndex = dayRecords.findIndex((record) => record.time === time)
      if (recordIndex < 0) {
        dayRecords.push({ time })
        recordIndex = dayRecords.length - 1
      }
      const recordValue =
        (field === 'medicine' || field === 'mood') && normalized === '—'
          ? ''
          : normalized
      dayRecords[recordIndex][field] = recordValue
      this.medicationRecordsMap[day] = dayRecords
      this.selectedCalendarDetail = this.buildSelectedDayDetail(day)
      this.updateDayMedicationStatus(day, dayRecords)

      this.persistCurrentMonthDataToCache()
      this.rebuildMedicationCalendarCells()
      this.updateMedicationStatusHint()

      this.closeScheduleFieldEditor()
      uni.showToast({ title: '已更新日程', icon: 'success' })
    },
    /**
     * Toggle medication taken flag for selected day and slot.
     * @param {{time: string, medicine?: string, mood?: string}} item - Displayed schedule row payload.
     * @returns {void}
     */
    toggleScheduleTaken(item) {
      if (!item || !item.time) return
      const day = this.selectedCalendarDay
      if (!day) return
      if (this.isCalendarCellAfterToday(day)) {
        uni.showToast({ title: '未来日期不可提前标记已服药', icon: 'none' })
        return
      }

      const safeMedicine = item.medicine && item.medicine !== '待补充' ? item.medicine : '待补充'
      const safeMood = item.mood && item.mood !== '—' ? item.mood : ''
      const dayRecords = Array.isArray(this.medicationRecordsMap[day])
        ? this.medicationRecordsMap[day].map((record) => ({ ...record }))
        : []
      const recordIndex = dayRecords.findIndex((record) => record.time === item.time)

      let nextTaken = true
      if (recordIndex >= 0) {
        nextTaken = !dayRecords[recordIndex].taken
        dayRecords[recordIndex] = {
          ...dayRecords[recordIndex],
          taken: nextTaken,
        }
      } else {
        dayRecords.push({
          time: item.time,
          medicine: safeMedicine,
          mood: safeMood,
          taken: true,
        })
      }

      dayRecords.sort((a, b) => String(a.time).localeCompare(String(b.time)))
      this.medicationRecordsMap[day] = dayRecords
      this.updateDayMedicationStatus(day, dayRecords)
      this.persistCurrentMonthDataToCache()
      this.rebuildMedicationCalendarCells()
      this.selectedCalendarDetail = this.buildSelectedDayDetail(day)
      this.updateMedicationStatusHint()
      uni.showToast({ title: nextTaken ? '已标记为已服药' : '已标记为未服药', icon: 'success' })
    },
    compareCalendarDayWithToday(day) {
      if (!day) return 0
      const today = new Date()
      const yearDiff = this.currentCalendarYear - today.getFullYear()
      if (yearDiff !== 0) return yearDiff
      const monthDiff = this.currentCalendarMonth - today.getMonth()
      if (monthDiff !== 0) return monthDiff
      return day - today.getDate()
    },
    isCalendarCellBeforeToday(day) {
      return this.compareCalendarDayWithToday(day) <= 0
    },
    isCalendarCellAfterToday(day) {
      return this.compareCalendarDayWithToday(day) > 0
    },
    focusScheduleByTime(time) {
      this.activeScheduleTime = time
      this.activeSchedulePulse = false
      this.$nextTick(() => {
        this.activeSchedulePulse = true
        setTimeout(() => {
          this.activeSchedulePulse = false
        }, 320)
        uni.pageScrollTo({
          selector: `#schedule-row-${time.replace(':', '')}`,
          duration: 220,
        })
      })
    },
    buildSelectedDayDetail(day) {
      const records = this.medicationRecordsMap[day] || []
      const taken = !!this.medicationStatusMap[day]
      const dateText = `${this.currentCalendarYear}-${String(this.currentCalendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
      return {
        day,
        dateText,
        taken,
        records,
      }
    },
    getMedicationMonthData(year, month) {
      const daysInMonth = new Date(year, month + 1, 0).getDate()
      const statusMap = {}
      const recordsMap = {}
      const sampleDayRecords = {
        3: [
          { time: '08:30', medicine: '左旋多巴 1片', mood: '平稳', taken: true },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: '轻松', taken: true },
          { time: '19:00', medicine: '左旋多巴 1片', mood: '舒适', taken: true },
        ],
        8: [
          { time: '08:30', medicine: '左旋多巴 1片', mood: '平静', taken: true },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: '疲惫', taken: false },
          { time: '19:00', medicine: '左旋多巴 1片', mood: '稳定', taken: true },
        ],
        14: [
          { time: '08:30', medicine: '左旋多巴 1片', mood: '欠佳', taken: false },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: '好转', taken: true },
          { time: '19:00', medicine: '左旋多巴 1片', mood: '平稳', taken: true },
        ],
        21: [
          { time: '08:30', medicine: '左旋多巴 1片', mood: '舒缓', taken: true },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: '平稳', taken: true },
          { time: '19:00', medicine: '金刚烷胺 1片', mood: '烦躁', taken: false },
        ],
        27: [
          { time: '08:30', medicine: '左旋多巴 1片', mood: '良好', taken: true },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: '轻松', taken: true },
          { time: '19:00', medicine: '左旋多巴 1片', mood: '安稳', taken: true },
        ],
      }

      for (let day = 1; day <= daysInMonth; day++) {
        const sampleRecords = sampleDayRecords[day]
        if (sampleRecords) {
          recordsMap[day] = sampleRecords.map((record) => ({ ...record }))
          statusMap[day] = sampleRecords.every((record) => record.taken)
          continue
        }

        const morningTaken = day % 5 !== 0
        const noonTaken = day % 7 !== 0
        const nightTaken = day % 6 !== 0
        const allTaken = morningTaken && noonTaken && nightTaken

        statusMap[day] = allTaken
        recordsMap[day] = [
          { time: '08:30', medicine: '左旋多巴 1片', mood: morningTaken ? '平稳' : '低落', taken: morningTaken },
          { time: '14:30', medicine: '普拉克索 0.5片', mood: noonTaken ? '轻松' : '疲惫', taken: noonTaken },
          { time: '19:00', medicine: '左旋多巴 1片', mood: nightTaken ? '安稳' : '烦闷', taken: nightTaken },
        ]
      }

      return { statusMap, recordsMap }
    },
    loadLocalSettings() {
      const savedProfile = uni.getStorageSync('carepal_profile')
      if (savedProfile && typeof savedProfile === 'object') {
        this.profile = { ...this.profile, ...savedProfile }
      }

      if (!this.profile.emergencyEmail && typeof this.profile.emergencyPhone === 'string') {
        const legacy = this.profile.emergencyPhone.trim()
        const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(legacy)
        if (validEmail) {
          this.profile.emergencyEmail = legacy
        }
      }

      const elderMode = uni.getStorageSync('carepal_elderMode')
      const darkMode = uni.getStorageSync('carepal_darkMode')
      this.elderMode = !!elderMode
      this.darkMode = !!darkMode
    },
    onPickAvatar() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const filePath = (res.tempFilePaths && res.tempFilePaths[0]) || ''
          if (!filePath) return
          this.profile.avatar = filePath
        },
      })
    },
    onSaveProfile() {
      uni.setStorageSync('carepal_profile', this.profile)
      uni.showToast({ title: '已保存', icon: 'success' })
    },
    beginEdit(field) {
      this.editField = field
      this.editValue = this.profile[field] || ''
    },
    cancelEdit() {
      this.editField = ''
      this.editValue = ''
    },
    applyEdit() {
      if (!this.editField) return
      const field = this.editField
      this.profile[field] = (this.editValue || '').trim()
      this.cancelEdit()
      this.onSaveProfile()
    },
  },
}
</script>

<style>
.carepal-page {
  --cp-font-family: 'HarmonyOS Sans SC', 'MiSans', 'Source Han Sans SC', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --cp-text-primary: #122f54;
  --cp-text-secondary: #3f5274;
  --cp-text-muted: #70809a;
  --cp-surface-lv1: rgba(255, 255, 255, 0.88);
  --cp-surface-lv2: #f5f8ff;
  --cp-surface-lv3: #ffffff;
  --cp-glow-soft: rgba(56, 124, 255, 0.12);
  --cp-motion-fast: 0.2s;
  --cp-motion-mid: 0.3s;
  min-height: 100vh;
  background: radial-gradient(circle at 0 0, #e6f3ff 0, #f5f9ff 35%, #ffffff 70%);
  padding: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  font-size: 28rpx;
  font-family: var(--cp-font-family);
  position: relative;
  overflow: hidden;
  transition: background 0.35s ease, color 0.35s ease;
}

.carepal-page :deep(.var-button),
.carepal-page :deep(.var-input__input),
.carepal-page :deep(.var-input__placeholder) {
  font-family: var(--cp-font-family);
}

.carepal-page::before,
.carepal-page::after {
  content: '';
  position: absolute;
  width: 520rpx;
  height: 520rpx;
  border-radius: 50%;
  filter: blur(40rpx);
  pointer-events: none;
  z-index: 0;
}

.carepal-page::before {
  top: -180rpx;
  right: -120rpx;
  background: radial-gradient(circle, rgba(66, 160, 255, 0.16) 0, rgba(66, 160, 255, 0) 70%);
}

.carepal-page::after {
  bottom: -220rpx;
  left: -120rpx;
  background: radial-gradient(circle, rgba(76, 211, 193, 0.14) 0, rgba(76, 211, 193, 0) 70%);
}

/* 长辈关怀模式：整体字号上调一档（不改布局结构） */
.carepal-page.is-elder {
  font-size: 42rpx;
}

.carepal-page.is-elder .carepal-header-title,
.carepal-page.is-elder .carepal-panel-title,
.carepal-page.is-elder .carepal-chat-title {
  font-size: 56rpx;
}

.carepal-page.is-elder .carepal-panel-subtitle,
.carepal-page.is-elder .carepal-chat-status,
.carepal-page.is-elder .carepal-nav-desc,
.carepal-page.is-elder .carepal-profile-label,
.carepal-page.is-elder .carepal-profile-value,
.carepal-page.is-elder .carepal-ocr-hint,
.carepal-page.is-elder .carepal-ocr-explain-subtitle {
  font-size: 40rpx;
}

.carepal-page.is-elder .carepal-chat-bubble,
.carepal-page.is-elder .carepal-table-head,
.carepal-page.is-elder .carepal-table-row,
.carepal-page.is-elder .carepal-calendar-title,
.carepal-page.is-elder .carepal-calendar-subtitle,
.carepal-page.is-elder .carepal-calendar-day,
.carepal-page.is-elder .carepal-ocr-explain-placeholder,
.carepal-page.is-elder .carepal-ocr-explain-text {
  font-size: 42rpx;
}

.carepal-page.is-elder .carepal-chat-textarea {
  font-size: 42rpx;
}

.carepal-page.is-elder .carepal-sidebar-title {
  font-size: 40rpx;
}

.carepal-page.is-elder .carepal-nav-label {
  font-size: 46rpx;
}

.carepal-page.is-elder .carepal-profile-title {
  font-size: 44rpx;
}

.carepal-page.is-elder .carepal-ocr-text {
  font-size: 42rpx;
}

.carepal-page.is-elder .carepal-ocr-explain-title {
  font-size: 44rpx;
}

.carepal-page.is-elder .carepal-weekly-section-title {
  font-size: 44rpx;
}

.carepal-page.is-elder .carepal-weekly-hint,
.carepal-page.is-elder .carepal-weekly-label,
.carepal-page.is-elder .carepal-weekly-score-prompt,
.carepal-page.is-elder .carepal-weekly-score-desc,
.carepal-page.is-elder .carepal-weekly-file-name,
.carepal-page.is-elder .carepal-weekly-question-item,
.carepal-page.is-elder .carepal-weekly-result-text {
  font-size: 38rpx;
}

.carepal-page.is-elder .carepal-weekly-result-encouragement {
  font-size: 46rpx;
}

.carepal-page.is-elder .carepal-weekly-score-title {
  font-size: 40rpx;
}

.carepal-page.is-elder .carepal-weekly-page-title {
  font-size: 40rpx;
}

.carepal-page.is-elder .carepal-weekly-page-index {
  font-size: 34rpx;
}

.carepal-page.is-elder .carepal-weekly-textarea {
  font-size: 40rpx;
  min-height: 200rpx;
}

.carepal-page.is-elder .carepal-weekly-voice-btn {
  min-height: 98rpx;
  border-radius: 18rpx;
}

.carepal-page.is-elder .carepal-weekly-voice-btn :deep(.var-button__content) {
  font-size: 36rpx;
}

.carepal-page.is-elder .carepal-weekly-score-btn {
  min-width: 120rpx;
  height: 66rpx;
}

.carepal-page.is-elder .carepal-weekly-score-btn :deep(.var-button__content) {
  font-size: 34rpx;
}

.carepal-page.is-elder .carepal-weekly-page-tab-btn :deep(.var-button__content),
.carepal-page.is-elder .carepal-weekly-page-action-btn :deep(.var-button__content) {
  font-size: 32rpx;
}

/* 长辈关怀模式下：同步放大输入条高度，避免大字体拥挤 */
.carepal-page.is-elder .carepal-chat-input-main {
  height: 106rpx;
  min-height: 106rpx;
}

.carepal-page.is-elder .carepal-chat-textarea {
  line-height: 1.4;
}

.carepal-page.is-elder .carepal-chat-send {
  height: 106rpx;
}

/* 覆盖 Varlet Input 内部字号（长辈模式也一起放大） */
.carepal-page.is-elder :deep(.var-input__input),
.carepal-page.is-elder :deep(.var-input__placeholder) {
  font-size: 42rpx;
}

/* 暗夜模式：只做必要的背景/文字反色，不引入新页面 */
.carepal-page.is-dark {
  --cp-text-primary: rgba(241, 245, 255, 0.96);
  --cp-text-secondary: rgba(220, 230, 247, 0.84);
  --cp-text-muted: rgba(199, 212, 232, 0.68);
  --cp-surface-lv1: rgba(12, 18, 32, 0.9);
  --cp-surface-lv2: rgba(255, 255, 255, 0.08);
  --cp-surface-lv3: rgba(255, 255, 255, 0.06);
  --cp-glow-soft: rgba(59, 130, 246, 0.2);
  background: radial-gradient(circle at 0 0, #0f172a 0, #070d19 45%, #050812 85%);
  color: #e6eefc;
}

.carepal-page.is-dark::before {
  background: radial-gradient(circle, rgba(59, 130, 246, 0.18) 0, rgba(59, 130, 246, 0) 70%);
}

.carepal-page.is-dark::after {
  background: radial-gradient(circle, rgba(20, 184, 166, 0.16) 0, rgba(20, 184, 166, 0) 70%);
}

.carepal-page.is-dark .carepal-header {
  background: rgba(7, 10, 18, 0.9);
  box-shadow: 0 14rpx 36rpx rgba(0, 0, 0, 0.44);
}

.carepal-page.is-dark .carepal-header-title {
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-header-subtitle {
  color: rgba(230, 238, 252, 0.72);
}

.carepal-page.is-dark .carepal-header-logo {
  border-color: rgba(125, 211, 252, 0.36);
  background: rgba(8, 14, 26, 0.92);
  box-shadow: 0 6rpx 14rpx rgba(59, 130, 246, 0.28);
}

.carepal-page.is-dark .carepal-header-logo-image {
  filter: saturate(1.08) brightness(1.06);
}

.carepal-page.is-dark .carepal-header-chip {
  color: rgba(230, 238, 252, 0.86);
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(125, 211, 252, 0.34);
}

.carepal-page.is-dark .carepal-header-user {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(241, 245, 255, 0.82);
}

.carepal-page.is-dark .carepal-header-user-dot {
  background: #34d399;
  box-shadow: 0 0 0 6rpx rgba(52, 211, 153, 0.2);
}

.carepal-page.is-dark .carepal-sidebar,
.carepal-page.is-dark .carepal-panel,
.carepal-page.is-dark .carepal-chat {
  background: rgba(10, 14, 24, 0.94);
  box-shadow: 0 24rpx 56rpx rgba(0, 0, 0, 0.52);
  border: 1rpx solid rgba(255, 255, 255, 0.08);
}

.carepal-page.is-dark .carepal-sidebar::before {
  background: radial-gradient(circle, rgba(56, 189, 248, 0.22) 0%, rgba(56, 189, 248, 0) 72%);
}

.carepal-page.is-dark .carepal-nav-button {
  border-color: rgba(125, 211, 252, 0.28);
  box-shadow: 0 10rpx 22rpx rgba(0, 0, 0, 0.26);
}

.carepal-page.is-dark .carepal-nav-button.is-active {
  border-color: rgba(186, 230, 253, 0.58);
  box-shadow: 0 14rpx 30rpx rgba(125, 211, 252, 0.24);
}

.carepal-page.is-dark .carepal-nav-icon-wrap {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(125, 211, 252, 0.32);
  box-shadow: 0 6rpx 14rpx rgba(0, 0, 0, 0.24);
}

.carepal-page.is-dark .carepal-nav-icon-wrap.is-active {
  background: linear-gradient(180deg, rgba(191, 219, 254, 0.24) 0%, rgba(125, 211, 252, 0.2) 100%);
  border-color: rgba(125, 211, 252, 0.58);
}

.carepal-page.is-dark .carepal-sidebar-title,
.carepal-page.is-dark .carepal-panel-title,
.carepal-page.is-dark .carepal-chat-title,
.carepal-page.is-dark .carepal-profile-title,
.carepal-page.is-dark .carepal-ocr-explain-title {
  color: rgba(241, 245, 255, 0.95);
}

.carepal-page.is-dark .carepal-panel-subtitle,
.carepal-page.is-dark .carepal-chat-status,
.carepal-page.is-dark .carepal-ocr-hint,
.carepal-page.is-dark .carepal-ocr-explain-subtitle {
  color: rgba(230, 238, 252, 0.74);
}

.carepal-page.is-dark .carepal-chat-body,
.carepal-page.is-dark .carepal-table,
.carepal-page.is-dark .carepal-ocr-drop,
.carepal-page.is-dark .carepal-ocr-explain,
.carepal-page.is-dark .carepal-ocr-explain-body {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.16);
}

.carepal-page.is-dark .carepal-chat-body::-webkit-scrollbar-track {
  background: rgba(230, 238, 252, 0.12);
}

.carepal-page.is-dark .carepal-chat-body::-webkit-scrollbar-thumb {
  background: rgba(125, 211, 252, 0.56);
}

.carepal-page.is-dark .carepal-chat-body::-webkit-scrollbar-thumb:hover {
  background: rgba(125, 211, 252, 0.72);
}

.carepal-page.is-dark .carepal-chat-bubble {
  background: #0b1220;
  color: #ffffff;
}

.carepal-page.is-dark .carepal-chat-msg.is-ai .carepal-chat-bubble {
  background: #0b1220;
  color: #ffffff;
  box-shadow: 0 4rpx 14rpx rgba(0, 0, 0, 0.22);
}

.carepal-page.is-dark .carepal-chat-msg.is-user .carepal-chat-bubble {
  background: #0b1220;
  color: #ffffff;
}

.carepal-page.is-dark .carepal-chat-tts-btn {
  background: rgba(125, 211, 252, 0.18);
  color: #dbeafe;
}

.carepal-page.is-dark .carepal-chat-voice-bar {
  background: rgba(125, 211, 252, 0.16);
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-chat-msg.is-user .carepal-chat-voice-bar {
  background: #0b1220;
  color: #ffffff;
}

.carepal-page.is-dark .carepal-chat-voice-text {
  color: rgba(230, 238, 252, 0.76);
}

.carepal-page.is-dark .carepal-chat-input-main {
  background: rgba(255, 255, 255, 0.08);
}

.carepal-page.is-dark .carepal-chat-hold-to-talk {
  background: rgba(125, 211, 252, 0.12);
  border-color: rgba(125, 211, 252, 0.3);
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-chat-textarea {
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-chat-textarea::placeholder {
  color: rgba(230, 238, 252, 0.62);
}

.carepal-page.is-dark .carepal-ocr-preview {
  background: rgba(255, 255, 255, 0.06);
}

.carepal-page.is-dark .carepal-ocr-submit-btn {
  border-color: rgba(125, 211, 252, 0.28);
}

/* 暗夜模式：补齐表格/OCR/我们模块的文字对比度 */
.carepal-page.is-dark .carepal-table-head {
  background: rgba(255, 255, 255, 0.10);
  color: rgba(241, 245, 255, 0.92);
}

.carepal-page.is-dark .carepal-table-row {
  color: rgba(230, 238, 252, 0.86);
}

.carepal-page.is-dark .carepal-table-row:nth-child(odd) {
  background: rgba(255, 255, 255, 0.05);
}

.carepal-page.is-dark .carepal-table-row.is-highlight {
  background: rgba(125, 211, 252, 0.22) !important;
  box-shadow: inset 0 0 0 1rpx rgba(125, 211, 252, 0.55);
}

.carepal-page.is-dark .carepal-table-row.is-pulse {
  animation: carepal-table-pulse-dark 0.32s ease;
}

.carepal-page.is-dark .carepal-calendar-card {
  background:
    radial-gradient(circle at 88% -10%, rgba(96, 165, 250, 0.22) 0, rgba(96, 165, 250, 0) 50%),
    linear-gradient(180deg, rgba(33, 45, 73, 0.62) 0%, rgba(255, 255, 255, 0.09) 100%);
  box-shadow: inset 0 0 0 1rpx rgba(255, 255, 255, 0.16), 0 10rpx 24rpx rgba(0, 0, 0, 0.22);
}

.carepal-page.is-dark .carepal-calendar-inline-tip {
  color: rgba(219, 233, 252, 0.84);
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.22) 0%, rgba(125, 211, 252, 0.16) 100%);
  border-color: rgba(147, 197, 253, 0.28);
}

.carepal-page.is-dark .carepal-calendar-header {
  border-bottom-color: rgba(147, 197, 253, 0.3);
}

.carepal-page.is-dark .carepal-calendar-weekday {
  color: rgba(221, 233, 250, 0.9);
  background: linear-gradient(180deg, rgba(96, 165, 250, 0.2) 0%, rgba(147, 197, 253, 0.14) 100%);
  border-color: rgba(147, 197, 253, 0.26);
}

.carepal-page.is-dark .carepal-calendar-cell {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.13) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: rgba(186, 230, 253, 0.26);
  box-shadow: 0 10rpx 18rpx rgba(0, 0, 0, 0.28), inset 0 1rpx 0 rgba(191, 219, 254, 0.24);
}

.carepal-page.is-dark .carepal-calendar-cell.is-ok {
  border-radius: 18rpx;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.13) 0%, rgba(255, 255, 255, 0.08) 100%);
  border-color: transparent;
  box-shadow: 0 8rpx 16rpx rgba(0, 0, 0, 0.24);
}

.carepal-page.is-dark .carepal-calendar-cell.is-miss {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.28) 0%, rgba(153, 27, 27, 0.2) 100%);
  border-color: rgba(252, 165, 165, 0.45);
}

.carepal-page.is-dark .carepal-calendar-cell.is-unrecorded {
  background: transparent;
  border: none;
  border-radius: 18rpx;
  box-shadow: none;
}

.carepal-page.is-dark .carepal-calendar-cell.is-empty {
  border: none;
  box-shadow: none;
}

.carepal-page.is-dark .carepal-calendar-cell.is-selected {
  border-color: rgba(191, 219, 254, 0.86);
  box-shadow: 0 0 0 4rpx rgba(96, 165, 250, 0.26), 0 14rpx 26rpx rgba(29, 78, 216, 0.34);
  background: linear-gradient(180deg, #5fb1ff 0%, #3f95f5 100%);
}

.carepal-page.is-dark .carepal-calendar-cell.is-before-today .carepal-calendar-day {
  font-size: 36rpx;
  color: var(--cp-text-secondary);
}

.carepal-page.is-dark .carepal-calendar-cell.is-after-today .carepal-calendar-day {
  font-size: 36rpx;
  color: var(--cp-text-secondary);
}

.carepal-page.is-dark .carepal-calendar-day-note {
  color: rgba(230, 238, 252, 0.82);
}

.carepal-page.is-dark .carepal-calendar-detail {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.06) 100%);
  border-color: rgba(255, 255, 255, 0.16);
}

.carepal-page.is-dark .carepal-calendar-detail-item {
  background: rgba(59, 130, 246, 0.18);
  border-color: rgba(125, 211, 252, 0.22);
}

.carepal-page.is-dark .carepal-calendar-detail-status.is-ok {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.42);
}

.carepal-page.is-dark .carepal-calendar-detail-status.is-miss {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.22);
  border-color: rgba(248, 113, 113, 0.42);
}

.carepal-page.is-dark .carepal-calendar-year-item {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.2);
}

.carepal-page.is-dark .carepal-calendar-year-item.is-good {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.08) 100%);
}

.carepal-page.is-dark .carepal-calendar-year-item.is-warn {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.08) 100%);
}

.carepal-page.is-dark .carepal-calendar-year-item-title {
  color: rgba(241, 245, 255, 0.94);
}

.carepal-page.is-dark .carepal-calendar-year-item-meta,
.carepal-page.is-dark .carepal-calendar-year-title {
  color: rgba(230, 238, 252, 0.8);
}

.carepal-page.is-dark .carepal-calendar-year-progress {
  background: rgba(125, 211, 252, 0.22);
}

.carepal-page.is-dark .carepal-calendar-year-progress-fill {
  background: linear-gradient(90deg, #60a5fa 0%, #2dd4bf 100%);
}

.carepal-page.is-dark .carepal-calendar-year-item-rate {
  color: #c7ddff;
}

.carepal-page.is-dark .carepal-ocr-text,
.carepal-page.is-dark .carepal-ocr-explain-text {
  color: rgba(241, 245, 255, 0.90);
}

.carepal-page.is-dark .carepal-ocr-preview-hint,
.carepal-page.is-dark .carepal-ocr-explain-placeholder {
  color: rgba(230, 238, 252, 0.72);
}

.carepal-page.is-dark .carepal-profile-label {
  color: rgba(230, 238, 252, 0.74);
}

.carepal-page.is-dark .carepal-profile-value {
  color: rgba(241, 245, 255, 0.92);
}

.carepal-page.is-dark .carepal-profile :deep(.var-input__input) {
  color: rgba(241, 245, 255, 0.92);
}

.carepal-page.is-dark .carepal-profile :deep(.var-input__placeholder) {
  color: rgba(230, 238, 252, 0.62);
}

/* 三档文字对比：主文字/次文字/弱提示 */
.carepal-header-title,
.carepal-sidebar-title,
.carepal-panel-title,
.carepal-chat-title,
.carepal-profile-title,
.carepal-ocr-explain-title,
.carepal-ocr-text,
.carepal-profile-value,
.carepal-ocr-explain-text {
  color: var(--cp-text-primary);
}

.carepal-nav-label,
.carepal-profile-label,
.carepal-table-row,
.carepal-chat-textarea,
.carepal-matter-text {
  color: var(--cp-text-secondary);
}

.carepal-panel-subtitle,
.carepal-chat-status,
.carepal-ocr-hint,
.carepal-ocr-explain-subtitle,
.carepal-nav-desc,
.carepal-ocr-explain-placeholder,
.carepal-ocr-preview-hint,
.carepal-header-user {
  color: var(--cp-text-muted);
}

.carepal-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12rpx 20rpx;
  margin-bottom: 24rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12rpx);
  box-shadow: 0 14rpx 32rpx rgba(15, 35, 95, 0.12);
}

.carepal-header-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.carepal-header-brand {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.carepal-header-logo {
  width: 58rpx;
  height: 58rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid rgba(54, 180, 255, 0.22);
  overflow: hidden;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8rpx 18rpx rgba(54, 180, 255, 0.24);
}

.carepal-header-logo-image {
  width: 82%;
  height: 82%;
  display: block;
}

.carepal-monitor-layout {
  display: grid;
  grid-template-columns: 320rpx 1fr;
  gap: 22rpx;
  min-height: 720rpx;
}

.carepal-monitor-left {
  display: flex;
}

.carepal-monitor-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.7);
  border: 1rpx solid rgba(76, 157, 255, 0.2);
  border-radius: 22rpx;
  padding: 22rpx;
  box-sizing: border-box;
}

.carepal-monitor-card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
}

.carepal-monitor-actions {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  margin-top: 16rpx;
}

.carepal-monitor-btn {
  width: 100%;
}

.carepal-monitor-status-row {
  margin-top: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.carepal-monitor-status-label {
  color: var(--cp-text-secondary);
  font-size: 25rpx;
}

.carepal-monitor-status-pill {
  border-radius: 999rpx;
  padding: 6rpx 14rpx;
  font-size: 22rpx;
  border: 1rpx solid rgba(121, 136, 159, 0.28);
  color: #506789;
  background: rgba(231, 239, 251, 0.8);
}

.carepal-monitor-status-pill.is-running {
  color: #135545;
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(187, 247, 208, 0.7);
}

.carepal-monitor-status-pill.is-safe {
  color: #14532d;
  border-color: rgba(34, 197, 94, 0.34);
  background: rgba(220, 252, 231, 0.76);
}

.carepal-monitor-status-pill.is-alert {
  color: #7f1d1d;
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(254, 226, 226, 0.85);
}

.carepal-monitor-hint {
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: var(--cp-text-muted);
}

.carepal-monitor-right {
  min-width: 0;
}

.carepal-monitor-view {
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  border-radius: 24rpx;
  overflow: hidden;
  border: 1rpx solid rgba(76, 157, 255, 0.25);
  background: linear-gradient(140deg, rgba(245, 250, 255, 0.9) 0%, rgba(228, 242, 255, 0.8) 100%);
  position: relative;
}

.carepal-monitor-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.carepal-monitor-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  color: var(--cp-text-muted);
}

.carepal-monitor-placeholder-title {
  font-size: 34rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
}

.carepal-monitor-placeholder-text {
  font-size: 24rpx;
}

.carepal-page.is-dark .carepal-monitor-card {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(125, 211, 252, 0.24);
}

.carepal-page.is-dark .carepal-monitor-view {
  background: linear-gradient(145deg, rgba(17, 23, 38, 0.96) 0%, rgba(8, 14, 26, 0.92) 100%);
  border-color: rgba(125, 211, 252, 0.3);
}

.carepal-page.is-dark .carepal-monitor-status-pill {
  background: rgba(255, 255, 255, 0.09);
  color: #dbe9fb;
  border-color: rgba(148, 163, 184, 0.4);
}

.carepal-page.is-dark .carepal-monitor-status-pill.is-running {
  color: #bbf7d0;
  background: rgba(22, 101, 52, 0.32);
  border-color: rgba(52, 211, 153, 0.46);
}

.carepal-page.is-dark .carepal-monitor-status-pill.is-safe {
  color: #bbf7d0;
  background: rgba(20, 83, 45, 0.44);
  border-color: rgba(74, 222, 128, 0.44);
}

.carepal-page.is-dark .carepal-monitor-status-pill.is-alert {
  color: #fecaca;
  background: rgba(127, 29, 29, 0.45);
  border-color: rgba(248, 113, 113, 0.52);
}

.carepal-page.is-dark .carepal-monitor-placeholder-title {
  color: #e5effd;
}

.carepal-page.is-dark .carepal-monitor-placeholder-text,
.carepal-page.is-dark .carepal-monitor-hint,
.carepal-page.is-dark .carepal-monitor-status-label {
  color: rgba(219, 233, 251, 0.76);
}

@media screen and (max-width: 900px) {
  .carepal-monitor-layout {
    grid-template-columns: 1fr;
    min-height: 0;
  }
}

.carepal-header-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2rpx;
}

.carepal-header-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #123055;
}

.carepal-header-subtitle {
  font-size: 22rpx;
  color: #6e7f9d;
}

.carepal-header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12rpx;
  font-size: 28rpx;
}

.carepal-sidebar-handle {
  z-index: 3;
}

.carepal-sidebar-handle--collapsed {
  position: absolute;
  left: 8rpx;
  top: 50%;
  transform: translateY(-50%) translateX(-12rpx);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.52s ease, transform 0.58s cubic-bezier(0.19, 1, 0.22, 1);
}

.carepal-sidebar-handle--expanded {
  position: absolute;
  right: 12rpx;
  top: 12rpx;
  opacity: 1;
  transition: opacity 0.48s ease, transform 0.54s ease;
}

.carepal-sidebar-toggle {
  width: 62rpx;
  height: 62rpx;
  min-width: 62rpx;
  border-radius: 50%;
  padding: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(241, 248, 255, 0.92) 100%);
  border: 1rpx solid rgba(76, 157, 255, 0.32);
  box-shadow: 0 10rpx 22rpx rgba(32, 84, 170, 0.2), inset 0 1rpx 0 rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8rpx);
  transition: transform 0.2s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.carepal-sidebar-toggle--hint {
  width: auto;
  min-width: 118rpx;
  padding: 0 18rpx 0 14rpx;
  border-radius: 999rpx;
}

.carepal-sidebar-toggle-text {
  margin-left: 8rpx;
  font-size: 22rpx;
  font-weight: 600;
  color: #2a4f82;
  letter-spacing: 0.8rpx;
}

.carepal-sidebar-toggle:active {
  transform: scale(0.96);
  box-shadow: 0 6rpx 12rpx rgba(32, 84, 170, 0.16), inset 0 1rpx 0 rgba(255, 255, 255, 0.6);
}

.carepal-sidebar-toggle-icon {
  width: 18rpx;
  height: 18rpx;
  position: relative;
}

.carepal-sidebar-toggle-icon::before,
.carepal-sidebar-toggle-icon::after {
  content: '';
  position: absolute;
  right: 2rpx;
  width: 11rpx;
  height: 3rpx;
  border-radius: 999rpx;
  background: #2a4f82;
  transform-origin: right center;
  transition: transform 0.22s ease, background 0.22s ease;
}

.carepal-sidebar-toggle-icon::before {
  top: 5rpx;
  transform: rotate(45deg);
}

.carepal-sidebar-toggle-icon::after {
  top: 11rpx;
  transform: rotate(-45deg);
}

.carepal-sidebar-toggle-icon.is-open::before {
  transform: rotate(-45deg);
}

.carepal-sidebar-toggle-icon.is-open::after {
  transform: rotate(45deg);
}

.carepal-page.is-dark .carepal-sidebar-toggle {
  background: linear-gradient(180deg, rgba(36, 52, 84, 0.9) 0%, rgba(24, 35, 58, 0.92) 100%);
  border-color: rgba(125, 211, 252, 0.45);
  box-shadow: 0 10rpx 24rpx rgba(0, 0, 0, 0.35), inset 0 1rpx 0 rgba(191, 219, 254, 0.24);
}

.carepal-page.is-dark .carepal-sidebar-identity {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.24) 0%, rgba(20, 184, 166, 0.2) 100%);
  border-color: rgba(125, 211, 252, 0.34);
}

.carepal-page.is-dark .carepal-sidebar-identity-name {
  color: rgba(241, 245, 255, 0.94);
}

.carepal-page.is-dark .carepal-sidebar-toggle-icon::before,
.carepal-page.is-dark .carepal-sidebar-toggle-icon::after {
  background: #dbeafe;
}

.carepal-page.is-dark .carepal-sidebar-toggle-text {
  color: #dbeafe;
}

.carepal-header-chip {
  height: 56rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  font-size: 24rpx;
  color: #1f3e69;
  background: rgba(76, 157, 255, 0.1);
  border: 1rpx solid rgba(76, 157, 255, 0.26);
}

.carepal-header-link {
  color: #3c7dff;
}

.carepal-header-user {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #f0f4ff;
  color: #4b5875;
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.carepal-header-user-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 6rpx rgba(16, 185, 129, 0.16);
}

.carepal-shell {
  width: 100%;
  flex: 1;
  position: relative;
  z-index: 1;
}

.carepal-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to right, rgba(76, 157, 255, 0.05) 1rpx, transparent 1rpx),
    linear-gradient(to bottom, rgba(76, 157, 255, 0.05) 1rpx, transparent 1rpx);
  background-size: 48rpx 48rpx;
  opacity: 0.22;
  z-index: 0;
}

.carepal-main {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 24rpx;
  padding: 0 36rpx 16rpx;
  min-height: calc(100vh - 100rpx);
  position: relative;
  z-index: 1;
}

.carepal-main-left {
  flex: 2.5;
  display: flex;
  min-width: 0;
  transition: all 0.62s cubic-bezier(0.19, 1, 0.22, 1);
}

.carepal-main-right {
  flex: 7.5;
  min-width: 0;
  min-height: 0;
  display: flex;
  transition: all 0.62s cubic-bezier(0.19, 1, 0.22, 1);
  transform: translateX(0);
  will-change: transform;
}

.carepal-main.is-sidebar-expanded .carepal-main-right {
  transform: translateX(0);
}

.carepal-main.is-sidebar-collapsed .carepal-main-left {
  flex: 0;
  width: 0;
  max-width: 0;
  opacity: 0;
  overflow: hidden;
}

.carepal-camera-mask {
  position: fixed;
  inset: 0;
  background: rgba(7, 14, 30, 0.62);
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  box-sizing: border-box;
}
.carepal-camera-panel {
  width: min(920rpx, 100%);
  background: #ffffff;
  border-radius: 20rpx;
  box-shadow: 0 20rpx 40rpx rgba(0, 0, 0, 0.25);
  padding: 18rpx;
  box-sizing: border-box;
}
.carepal-camera-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #133357;
  margin-bottom: 12rpx;
}
.carepal-camera-video {
  width: 100%;
  height: 760rpx;
  border-radius: 14rpx;
  background: #0c1324;
  object-fit: cover;
}
.carepal-camera-actions {
  margin-top: 14rpx;
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
}
.carepal-camera-btn {
  min-width: 120rpx;
}

.carepal-main.is-sidebar-collapsed .carepal-main-right {
  flex: 1;
  transform: translateX(0);
}

.carepal-main.is-sidebar-collapsed .carepal-sidebar-handle--collapsed {
  transform: translateY(-50%) translateX(0);
  opacity: 1;
  pointer-events: auto;
}

.carepal-main.is-sidebar-collapsed .carepal-sidebar-handle--expanded {
  opacity: 0;
  transform: translateY(-8rpx);
  pointer-events: none;
}
/* 侧边模块导航 */
.carepal-sidebar {
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--cp-surface-lv1);
  border-radius: 24rpx;
  padding: 24rpx 20rpx;
  box-shadow: 0 24rpx 52rpx rgba(17, 38, 92, 0.12);
  border: 1rpx solid rgba(18, 48, 85, 0.06);
  backdrop-filter: blur(12rpx);
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
  transform: translateX(0);
  opacity: 1;
  transition: transform 0.64s cubic-bezier(0.19, 1, 0.22, 1), opacity 0.5s ease;
}

.carepal-sidebar-identity {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 18rpx;
  padding: 12rpx 14rpx;
  border-radius: 14rpx;
  background: linear-gradient(135deg, rgba(76, 157, 255, 0.12) 0%, rgba(60, 211, 193, 0.1) 100%);
  border: 1rpx solid rgba(76, 157, 255, 0.2);
}

.carepal-sidebar-identity-avatar {
  width: 58rpx;
  height: 58rpx;
  border-radius: 50%;
  background: #f0f4ff;
  flex: 0 0 auto;
}

.carepal-sidebar-identity-text {
  min-width: 0;
}

.carepal-sidebar-identity-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #1d3f6d;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.carepal-sidebar-identity-status {
  margin-top: 4rpx;
  font-size: 22rpx;
  color: var(--cp-text-muted);
}

.carepal-main.is-sidebar-collapsed .carepal-sidebar {
  transform: translateX(-28rpx);
  opacity: 0.5;
}

.carepal-sidebar::before {
  content: '';
  position: absolute;
  top: -120rpx;
  right: -80rpx;
  width: 240rpx;
  height: 240rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(76, 157, 255, 0.2) 0%, rgba(76, 157, 255, 0) 72%);
  pointer-events: none;
}

.carepal-sidebar-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #123055;
  margin-bottom: 20rpx;
  padding-right: 72rpx;
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
}

.carepal-sidebar-title::before {
  content: '';
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #96cbff 0%, #c8ecff 100%);
  box-shadow: 0 0 0 6rpx rgba(150, 203, 255, 0.2);
}

.carepal-nav-button {
  width: 100%;
  margin-bottom: 14rpx;
  padding: 20rpx 22rpx;
  height: 124rpx;
  border-radius: 18rpx;
  text-align: left;
  border: 1rpx solid rgba(150, 203, 255, 0.3);
  box-shadow: 0 10rpx 20rpx rgba(113, 159, 214, 0.14);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  box-sizing: border-box;
}

.carepal-nav-button:last-child {
  margin-bottom: 0;
}

.carepal-nav-button::before {
  content: '';
  position: absolute;
  left: 10rpx;
  top: 14rpx;
  bottom: 14rpx;
  width: 6rpx;
  border-radius: 999rpx;
  background: linear-gradient(180deg, #8ec4ff 0%, #c5ebff 100%);
  opacity: 0;
  transform: scaleY(0.4);
  transition: opacity var(--cp-motion-mid) ease, transform var(--cp-motion-mid) ease;
}

.carepal-nav-button.is-active {
  border-color: rgba(140, 194, 255, 0.62);
  box-shadow: 0 14rpx 30rpx rgba(126, 176, 230, 0.28);
}

.carepal-nav-button.is-active::before {
  opacity: 1;
  transform: scaleY(1);
}

.carepal-page.is-elder .carepal-nav-button {
  height: 146rpx;
  padding: 24rpx 22rpx;
}

/* 覆盖 Varlet Button 内部内容容器，确保内容从左侧开始排 */
.carepal-nav-button .var-button__content {
  width: 100% !important;
  justify-content: flex-start !important;
}

.carepal-nav-content {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  gap: 16rpx;
  min-height: 76rpx;
}

.carepal-nav-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  flex: 1;
  min-width: 0;
}

.carepal-nav-icon-wrap {
  width: 76rpx;
  height: 76rpx;
  border-radius: 20rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(76, 157, 255, 0.2);
  box-shadow: 0 6rpx 14rpx rgba(76, 157, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.carepal-nav-icon-wrap.is-active {
  background: linear-gradient(180deg, rgba(255, 255, 255, 1) 0%, rgba(236, 246, 255, 0.98) 100%);
  border-color: rgba(76, 157, 255, 0.48);
  box-shadow: 0 8rpx 18rpx rgba(76, 157, 255, 0.22);
}

.carepal-nav-icon {
  width: 52rpx;
  height: 52rpx;
}

.carepal-nav-label {
  font-size: 38rpx;
  font-weight: 600;
  line-height: 1.25;
  width: 100%;
  text-align: left;
  letter-spacing: 0.4rpx;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.carepal-nav-desc {
  margin-top: 6rpx;
  font-size: 30rpx;
  line-height: 1.35;
  opacity: 0.84;
  text-align: left;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 通用右侧面板 */
.carepal-panel {
  background: var(--cp-surface-lv1);
  border-radius: 24rpx;
  box-shadow: 0 24rpx 56rpx rgba(17, 38, 92, 0.14);
  border: 1rpx solid rgba(18, 48, 85, 0.06);
  backdrop-filter: blur(10rpx);
  position: relative;
  padding: 24rpx 24rpx 12rpx;
  box-sizing: border-box;
  flex: 1;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.carepal-panel-header {
  margin-bottom: 16rpx;
}

.carepal-panel-title {
  font-size: 40rpx;
  font-weight: 600;
  color: #123055;
  margin-bottom: 6rpx;
}

.carepal-panel-subtitle {
  font-size: 30rpx;
  color: #7a8499;
}

/* 日程表样式 */
.carepal-table {
  margin-top: 10rpx;
  border-radius: 18rpx;
  overflow: hidden;
  background: var(--cp-surface-lv2);
  box-shadow: inset 0 0 0 1rpx rgba(80, 122, 197, 0.12);
}

.carepal-table-head,
.carepal-table-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 18rpx 18rpx;
}

.carepal-table-col {
  min-width: 0;
  padding-right: 18rpx;
  box-sizing: border-box;
}

.carepal-table-col.matter {
  padding-right: 0;
}

.carepal-table-head {
  background: #e1e8ff;
  font-weight: 600;
  font-size: 28rpx;
}

.carepal-table-row {
  font-size: 28rpx;
}

.carepal-table-row:nth-child(odd) {
  background: #fdfdff;
}

.carepal-table-row.is-highlight {
  background: rgba(76, 157, 255, 0.18) !important;
  box-shadow: inset 0 0 0 1rpx rgba(76, 157, 255, 0.45);
}

.carepal-table-row.is-pulse {
  animation: carepal-table-pulse-light 0.32s ease;
}

@keyframes carepal-table-pulse-light {
  0% {
    transform: scale(1);
    box-shadow: inset 0 0 0 1rpx rgba(76, 157, 255, 0.35);
  }
  50% {
    transform: scale(1.01);
    box-shadow: inset 0 0 0 1rpx rgba(76, 157, 255, 0.72), 0 0 0 5rpx rgba(76, 157, 255, 0.16);
  }
  100% {
    transform: scale(1);
    box-shadow: inset 0 0 0 1rpx rgba(76, 157, 255, 0.45);
  }
}

@keyframes carepal-table-pulse-dark {
  0% {
    transform: scale(1);
    box-shadow: inset 0 0 0 1rpx rgba(125, 211, 252, 0.45);
  }
  50% {
    transform: scale(1.01);
    box-shadow: inset 0 0 0 1rpx rgba(125, 211, 252, 0.85), 0 0 0 5rpx rgba(125, 211, 252, 0.2);
  }
  100% {
    transform: scale(1);
    box-shadow: inset 0 0 0 1rpx rgba(125, 211, 252, 0.55);
  }
}

.carepal-table-col.time {
  flex: 2;
  text-align: center;
}

.carepal-table-col.medication {
  flex: 3;
  text-align: center;
}

.carepal-medication-name {
  font-size: 24rpx;
  color: var(--cp-text-muted);
  margin-bottom: 6rpx;
}

.carepal-table-col.bp {
  flex: 2;
  text-align: center;
}

.carepal-table-col.weight {
  flex: 2;
  text-align: center;
}

.carepal-table-col.symptom {
  flex: 2.5;
  text-align: center;
}

.carepal-table-col.mood {
  flex: 2;
  text-align: center;
}

.carepal-table-col.matter {
  flex: 3.2;
  text-align: left;
}

.carepal-table-col.time,
.carepal-table-col.medication,
.carepal-table-col.bp,
.carepal-table-col.weight,
.carepal-table-col.symptom,
.carepal-table-col.mood,
.carepal-table-col.matter {
  cursor: pointer;
}

.carepal-matter-text {
  margin-bottom: 8rpx;
}

.carepal-calendar-card {
  margin-top: 18rpx;
  border-radius: 24rpx;
  background:
    radial-gradient(circle at 88% -10%, rgba(76, 157, 255, 0.18) 0, rgba(76, 157, 255, 0) 48%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(245, 250, 255, 0.92) 100%);
  box-shadow: inset 0 0 0 1rpx rgba(80, 122, 197, 0.14), 0 14rpx 34rpx rgba(38, 78, 152, 0.1);
  padding: 16rpx;
  min-height: 980rpx;
  position: relative;
  overflow: hidden;
}

.carepal-calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
  padding-bottom: 12rpx;
  border-bottom: 1rpx dashed rgba(80, 122, 197, 0.24);
}

.carepal-calendar-controls {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.carepal-calendar-btn {
  height: 52rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
}

.carepal-calendar-title {
  font-size: 38rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
}

.carepal-calendar-subtitle {
  font-size: 32rpx;
  color: var(--cp-text-muted);
  margin-bottom: 12rpx;
}

.carepal-calendar-year-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10rpx;
  margin-bottom: 10rpx;
}

.carepal-calendar-year-title {
  font-size: 28rpx;
  color: var(--cp-text-secondary);
  font-weight: 600;
}

.carepal-calendar-year-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12rpx;
  margin-bottom: 14rpx;
}
.carepal-calendar-inline-tip {
  margin-top: 10rpx;
  padding: 10rpx 14rpx;
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #54759d;
  background: linear-gradient(135deg, rgba(222, 239, 255, 0.72) 0%, rgba(236, 247, 255, 0.86) 100%);
  border: 1rpx solid rgba(140, 194, 255, 0.28);
}
.carepal-calendar-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  background:
    radial-gradient(circle at 8% -6%, rgba(156, 208, 255, 0.34) 0, rgba(156, 208, 255, 0) 46%),
    radial-gradient(circle at 96% 8%, rgba(186, 228, 255, 0.34) 0, rgba(186, 228, 255, 0) 44%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(243, 249, 255, 0.97) 100%);
  border-left: 1rpx solid rgba(125, 176, 230, 0.24);
  box-shadow: -18rpx 0 38rpx rgba(25, 57, 102, 0.18);
  transform: translateX(104%);
  transition: transform 0.46s cubic-bezier(0.22, 1, 0.36, 1);
  z-index: 5;
  padding: 12rpx 10rpx 14rpx;
  box-sizing: border-box;
  overflow-y: auto;
  backdrop-filter: blur(6rpx);
}
.carepal-calendar-drawer.is-open {
  transform: translateX(0);
}
.carepal-calendar-drawer-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
  padding: 10rpx 10rpx 12rpx;
  border-bottom: 1rpx dashed rgba(104, 155, 214, 0.26);
  background: linear-gradient(180deg, rgba(244, 250, 255, 0.98) 0%, rgba(244, 250, 255, 0.88) 100%);
  backdrop-filter: blur(10rpx);
}

.carepal-calendar-year-item {
  border-radius: 14rpx;
  border: 1rpx solid rgba(80, 122, 197, 0.2);
  background: rgba(255, 255, 255, 0.92);
  padding: 12rpx;
  min-height: 150rpx;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8rpx;
  box-shadow: 0 4rpx 12rpx rgba(43, 87, 166, 0.08);
}

.carepal-calendar-year-item.is-active {
  border-color: rgba(76, 157, 255, 0.65);
  box-shadow: 0 0 0 2rpx rgba(76, 157, 255, 0.2), 0 6rpx 14rpx rgba(76, 157, 255, 0.18);
}

.carepal-calendar-year-item.is-good {
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.95) 0%, rgba(242, 247, 255, 0.92) 100%);
}

.carepal-calendar-year-item.is-warn {
  background: linear-gradient(180deg, rgba(248, 251, 255, 0.95) 0%, rgba(242, 247, 255, 0.92) 100%);
}

.carepal-calendar-year-item-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
}

.carepal-calendar-year-item-meta {
  font-size: 24rpx;
  color: var(--cp-text-muted);
}

.carepal-calendar-year-progress {
  width: 100%;
  height: 10rpx;
  border-radius: 999rpx;
  background: rgba(76, 157, 255, 0.16);
  overflow: hidden;
}

.carepal-calendar-year-progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #4c9dff 0%, #3cd3c1 100%);
  transition: width 0.3s ease;
}

.carepal-calendar-year-item-rate {
  font-size: 24rpx;
  font-weight: 600;
  color: #2a4f82;
}

.carepal-calendar-weekdays,
.carepal-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10rpx;
  max-width: none;
  margin-left: auto;
  margin-right: auto;
}

.carepal-calendar-weekdays {
  margin-bottom: 12rpx;
}

.carepal-calendar-weekday {
  text-align: center;
  font-size: 24rpx;
  font-weight: 600;
  color: #4e6b91;
  padding: 8rpx 0;
  border-radius: 999rpx;
  background: linear-gradient(180deg, rgba(223, 239, 255, 0.7) 0%, rgba(237, 247, 255, 0.6) 100%);
  border: 1rpx solid rgba(150, 203, 255, 0.25);
}

.carepal-calendar-cell {
  width: 124rpx;
  height: 124rpx;
  min-height: 124rpx;
  border-radius: 50%;
  justify-self: center;
  border: none;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(239, 247, 255, 0.94) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rpx;
  box-sizing: border-box;
  box-shadow: 0 10rpx 18rpx rgba(105, 151, 204, 0.16);
  transition: transform var(--cp-motion-fast) ease, border-color var(--cp-motion-mid) ease, box-shadow var(--cp-motion-mid) ease, background var(--cp-motion-mid) ease;
}

.carepal-calendar-cell:not(.is-empty):hover {
  transform: translateY(-6rpx) scale(1.04);
  box-shadow: 0 18rpx 28rpx rgba(105, 151, 204, 0.32), inset 0 1rpx 0 rgba(255, 255, 255, 0.9);
}

.carepal-calendar-cell.is-empty {
  border: none;
  background: transparent;
  box-shadow: none;
}

.carepal-calendar-cell.is-selected {
  border-color: rgba(67, 156, 255, 0.86);
  box-shadow: 0 0 0 4rpx rgba(81, 170, 255, 0.24), 0 12rpx 24rpx rgba(74, 154, 230, 0.3);
  transform: translateY(-2rpx) scale(1.03);
  background: linear-gradient(180deg, #69b9ff 0%, #43a5ff 100%);
}

.carepal-calendar-cell.is-ok {
  border-radius: 18rpx;
  background: transparent;
  border: none;
  box-shadow: none;
}
.carepal-calendar-cell.is-ok:hover {
  transform: none;
  box-shadow: none;
}

.carepal-calendar-cell.is-miss {
  background: linear-gradient(180deg, #fff7f7 0%, #fff0f0 100%);
  border-color: rgba(236, 104, 104, 0.32);
}

.carepal-calendar-cell.is-unrecorded {
  border-radius: 18rpx;
  background: transparent;
  border: none;
  box-shadow: none;
}

.carepal-calendar-day {
  font-size: 32rpx;
  color: var(--cp-text-secondary);
  font-weight: 600;
}

.carepal-calendar-day-note {
  margin-top: 2rpx;
  font-size: 18rpx;
  line-height: 1.2;
  color: #7a8fa9;
}

.carepal-calendar-cell.is-selected .carepal-calendar-day {
  color: #ffffff;
  text-shadow: 0 2rpx 6rpx rgba(16, 95, 171, 0.3);
}

.carepal-calendar-cell.is-selected .carepal-calendar-day-note {
  color: rgba(255, 255, 255, 0.92);
}

.carepal-calendar-cell.is-before-today .carepal-calendar-day {
  font-size: 36rpx;
  color: var(--cp-text-secondary);
  font-weight: 700;
}

.carepal-calendar-cell.is-after-today .carepal-calendar-day {
  font-size: 36rpx;
  color: var(--cp-text-secondary);
  font-weight: 700;
}

.carepal-calendar-detail {
  margin-top: 16rpx;
  border-radius: 16rpx;
  background: transparent;
  border: 1rpx solid rgba(80, 122, 197, 0.24);
  box-shadow: none;
  padding: 14rpx;
.carepal-page.is-dark .carepal-calendar-cell.is-ok:hover {
  transform: none;
  box-shadow: none;
}
}

.carepal-calendar-detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 10rpx;
}

.carepal-calendar-detail-title {
  font-size: 26rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
}

.carepal-calendar-detail-status {
  font-size: 24rpx;
  padding: 4rpx 10rpx;
  border-radius: 999rpx;
  border: 1rpx solid transparent;
}

.carepal-calendar-detail-status.is-ok {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.carepal-calendar-detail-status.is-miss {
  color: #991b1b;
  background: #fee2e2;
  border-color: #fca5a5;
}

.carepal-calendar-detail-list {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.carepal-calendar-detail-item {
  display: grid;
  grid-template-columns: 92rpx 1fr 34rpx;
  gap: 10rpx;
  align-items: center;
  padding: 10rpx 12rpx;
  border-radius: 12rpx;
  background: rgba(76, 157, 255, 0.08);
  border: 1rpx solid rgba(76, 157, 255, 0.16);
}

.carepal-calendar-detail-time {
  font-size: 24rpx;
  color: var(--cp-text-muted);
}

.carepal-calendar-detail-medicine {
  font-size: 26rpx;
  color: var(--cp-text-secondary);
}

.carepal-calendar-detail-mark {
  font-size: 26rpx;
  font-weight: 700;
  text-align: center;
}

.carepal-calendar-detail-mark.is-ok {
  color: #16a34a;
}

.carepal-calendar-detail-mark.is-miss {
  color: #dc2626;
}

.carepal-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 3rpx 12rpx;
  border-radius: 12rpx;
  font-size: 22rpx;
  font-weight: 600;
  border: 1rpx solid transparent;
  white-space: nowrap;
  line-height: 1.2;
}

.carepal-status-pill.is-clickable {
  cursor: pointer;
  user-select: none;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.carepal-status-pill.is-clickable:hover {
  transform: translateY(-1rpx);
  box-shadow: 0 3rpx 8rpx rgba(30, 64, 175, 0.18);
}

.carepal-status-pill::before {
  content: '';
  width: 6rpx;
  height: 6rpx;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.85;
}

.carepal-status-pill.is-mini {
  padding: 2rpx 10rpx;
  border-radius: 10rpx;
  font-size: 20rpx;
  font-weight: 500;
}

.carepal-status-pill.is-done {
  color: #166534;
  background: #dcfce7;
  border-color: #86efac;
}

.carepal-status-pill.is-pending {
  color: #1d4ed8;
  background: #dbeafe;
  border-color: #93c5fd;
}

.carepal-status-pill.is-warning {
  color: #9a3412;
  background: #ffedd5;
  border-color: #fdba74;
}

.carepal-status-pill.is-miss {
  color: #991b1b;
  background: #fee2e2;
  border-color: #fca5a5;
}

.carepal-status-pill.is-info {
  color: #0f766e;
  background: #ccfbf1;
  border-color: #5eead4;
}

.carepal-page.is-dark .carepal-status-pill.is-done {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.18);
  border-color: rgba(34, 197, 94, 0.42);
}

.carepal-page.is-dark .carepal-status-pill.is-pending {
  color: #bfdbfe;
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(96, 165, 250, 0.42);
}

.carepal-page.is-dark .carepal-status-pill.is-warning {
  color: #fed7aa;
  background: rgba(249, 115, 22, 0.2);
  border-color: rgba(251, 146, 60, 0.44);
}

.carepal-page.is-dark .carepal-status-pill.is-miss {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.22);
  border-color: rgba(248, 113, 113, 0.45);
}

.carepal-page.is-dark .carepal-status-pill.is-info {
  color: #99f6e4;
  background: rgba(20, 184, 166, 0.2);
  border-color: rgba(45, 212, 191, 0.44);
}

/* OCR 上传区域样式 */
.carepal-ocr {
  flex: 1;
}

.carepal-ocr-layout {
  flex: 1;
  display: flex;
  gap: 24rpx;
  min-height: 0;
}

.carepal-ocr-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.carepal-ocr-right {
  flex: 1;
  min-width: 0;
  display: flex;
}

.carepal-ocr-layout.is-camera-live .carepal-ocr-drop {
  min-height: 860rpx;
}

.carepal-ocr-layout.is-camera-live .carepal-camera-video {
  height: 860rpx;
}

.carepal-ocr-drop {
  flex: 1;
  border-radius: 20rpx;
  border: 2rpx dashed #c3cde0;
  background: var(--cp-surface-lv2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 16rpx;
  min-height: 700rpx;
}

.carepal-ocr-drop-inner {
  text-align: center;
  padding: 30rpx 20rpx;
  width: 100%;
  box-sizing: border-box;
}
.carepal-ocr-drop-inner--camera {
  padding: 8rpx;
}

.carepal-ocr-preview {
  width: 100%;
  height: 760rpx;
  border-radius: 16rpx;
  background: #ffffff;
}

.carepal-ocr-camera-actions {
  margin-top: 12rpx;
  display: flex;
  justify-content: flex-end;
  gap: 12rpx;
}
.carepal-ocr-preview-hint {
  margin-top: 12rpx;
  font-size: 26rpx;
  color: #7a8499;
}

.carepal-ocr-icon {
  font-size: 60rpx;
  margin-bottom: 16rpx;
}

.carepal-ocr-text {
  font-size: 30rpx;
  color: #202742;
  margin-bottom: 8rpx;
}

.carepal-ocr-hint {
  font-size: 28rpx;
  color: #8a93a5;
}

.carepal-ocr-steps {
  margin-top: 18rpx;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.carepal-ocr-step {
  font-size: 26rpx;
  color: var(--cp-text-secondary);
  line-height: 1.5;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
}

.carepal-ocr-step-index {
  width: 34rpx;
  height: 34rpx;
  line-height: 34rpx;
  border-radius: 50%;
  text-align: center;
  font-size: 22rpx;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, #4c9dff 0%, #3cd3c1 100%);
}

.carepal-ocr-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 16rpx;
}

.carepal-ocr-submit-row {
  margin-top: 12rpx;
  display: flex;
  gap: 10rpx;
}

.carepal-ocr-submit-btn {
  flex: 1;
  min-height: 72rpx;
}

.carepal-ocr-btn {
  flex: 1;
}

.carepal-ocr-explain {
  flex: 1;
  border-radius: 20rpx;
  background: var(--cp-surface-lv2);
  border: 1rpx solid #eef0f6;
  padding: 18rpx;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.carepal-ocr-explain-title {
  font-size: 34rpx;
  font-weight: 600;
  color: #123055;
  margin-bottom: 6rpx;
}

.carepal-ocr-explain-subtitle {
  font-size: 28rpx;
  color: #7a8499;
  margin-bottom: 12rpx;
}

.carepal-ocr-explain-body {
  flex: 1;
  border-radius: 16rpx;
  background: var(--cp-surface-lv3);
  border: 1rpx solid #eef0f6;
  padding: 14rpx;
  box-sizing: border-box;
  overflow: auto;
}

.carepal-ocr-explain-placeholder {
  font-size: 28rpx;
  color: #8a93a5;
  line-height: 1.7;
}

.carepal-ocr-explain-text {
  font-size: 28rpx;
  color: #202742;
  line-height: 1.8;
}

/* 周报告样式 */
.carepal-weekly {
  flex: 1;
}

.carepal-weekly-card,
.carepal-weekly-result {
  border-radius: 20rpx;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(238, 246, 255, 0.9) 100%);
  border: 1rpx solid rgba(80, 122, 197, 0.18);
  padding: 18rpx;
  margin-bottom: 14rpx;
  box-shadow: 0 14rpx 28rpx rgba(37, 86, 168, 0.1);
}

.carepal-weekly-card--hero {
  background: linear-gradient(135deg, rgba(76, 157, 255, 0.2) 0%, rgba(60, 211, 193, 0.16) 100%);
  border-color: rgba(76, 157, 255, 0.3);
}

.carepal-weekly-card--voice {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(232, 244, 255, 0.92) 100%);
}

.carepal-weekly-section-title {
  font-size: 42rpx;
  font-weight: 600;
  color: var(--cp-text-primary);
  margin-bottom: 8rpx;
}
.carepal-weekly-page-fade-enter-active,
.carepal-weekly-page-fade-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}
.carepal-weekly-page-fade-enter-from,
.carepal-weekly-page-fade-leave-to {
  opacity: 0;
  transform: translateX(10rpx);
}

.carepal-weekly-hint {
  font-size: 34rpx;
  color: var(--cp-text-muted);
  width: 100%;
  line-height: 1.6;
  margin-bottom: 12rpx;
}

.carepal-weekly-voice-btn,
.carepal-weekly-submit {
  margin-top: 10rpx;
}

.carepal-weekly-voice-btn {
  min-height: 78rpx;
  border-radius: 16rpx;
  padding: 0 20rpx;
  max-width: 75%;
}

.carepal-weekly-voice-btn :deep(.var-button__content) {
  font-size: 30rpx;
  font-weight: 600;
}

.carepal-weekly-file-name {
  margin-top: 8rpx;
  font-size: 34rpx;
  color: var(--cp-text-secondary);
}

.carepal-weekly-question-list {
  margin: 12rpx 0 8rpx;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.carepal-weekly-question-item {
  font-size: 34rpx;
}

.carepal-weekly-score-list {
  margin-top: 8rpx;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.carepal-weekly-page-tabs {
  margin-top: 12rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.carepal-weekly-page-tab-btn {
  min-height: 68rpx;
  border-radius: 14rpx;
  border: 1rpx solid rgba(150, 203, 255, 0.28);
  box-shadow: 0 6rpx 14rpx rgba(145, 181, 226, 0.12);
}

.carepal-weekly-page-tab-btn :deep(.var-button__content) {
  font-size: 28rpx;
}

.carepal-chat-msg.is-user .carepal-chat-bubble-wrap,
.carepal-chat-msg.is-user .carepal-chat-voice-wrap {
  align-items: flex-end;
}

.carepal-chat-bubble-actions {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex: 0 0 auto;
}

.carepal-chat-copy-btn {
  width: 54rpx;
  height: 54rpx;
  border-radius: 50%;
  background: rgba(76, 157, 255, 0.14);
  color: #1e4f91;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: 600;
  padding: 0;
  box-sizing: border-box;
}

.carepal-chat-voice-transcript-btn {
  margin-left: auto;
  min-width: 108rpx;
  height: 46rpx;
  border-radius: 999rpx;
  padding: 0 14rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22rpx;
  background: rgba(18, 48, 85, 0.12);
  color: #123055;
}

.carepal-chat-msg.is-user .carepal-chat-voice-transcript-btn {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.carepal-chat-voice-text {
  margin-top: 2rpx;
  padding: 10rpx 12rpx;
  border-radius: 12rpx;
  background: rgba(76, 157, 255, 0.08);
  border: 1rpx solid rgba(76, 157, 255, 0.14);
}

.carepal-chat-copy-mask {
  position: fixed;
  inset: 0;
  z-index: 110;
  background: rgba(7, 14, 30, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22rpx;
  box-sizing: border-box;
}

.carepal-chat-copy-panel {
  width: min(680rpx, 100%);
  border-radius: 18rpx;
  background: #ffffff;
  padding: 18rpx;
  box-sizing: border-box;
  box-shadow: 0 20rpx 44rpx rgba(15, 28, 58, 0.24);
}

.carepal-chat-copy-title {
  font-size: 30rpx;
  color: #123055;
  font-weight: 600;
}

.carepal-chat-copy-textarea {
  margin-top: 12rpx;
  width: 100%;
  min-height: 260rpx;
  max-height: 380rpx;
  border-radius: 14rpx;
  background: #f5f9ff;
  border: 1rpx solid rgba(76, 157, 255, 0.24);
  padding: 14rpx;
  box-sizing: border-box;
  color: #20324c;
  font-size: 27rpx;
  line-height: 1.55;
}

.carepal-chat-copy-actions {
  margin-top: 14rpx;
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
}

.carepal-schedule-edit-mask {
  position: fixed;
  inset: 0;
  z-index: 115;
  background: rgba(7, 14, 30, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  box-sizing: border-box;
}

.carepal-schedule-edit-panel {
  width: min(640rpx, 100%);
  border-radius: 18rpx;
  background: #ffffff;
  box-shadow: 0 20rpx 42rpx rgba(15, 28, 58, 0.24);
  padding: 18rpx;
  box-sizing: border-box;
}

.carepal-schedule-edit-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #123055;
}

.carepal-schedule-edit-subtitle {
  margin-top: 6rpx;
  font-size: 26rpx;
  color: #6e7d96;
}

.carepal-schedule-edit-input {
  margin-top: 12rpx;
  height: 84rpx;
  border-radius: 14rpx;
  border: 1rpx solid rgba(76, 157, 255, 0.26);
  background: #f5f9ff;
  padding: 0 14rpx;
  box-sizing: border-box;
  font-size: 30rpx;
  color: #1c2a41;
}

.carepal-schedule-edit-actions {
  margin-top: 14rpx;
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
}

.carepal-page.is-dark .carepal-chat-copy-btn {
  background: rgba(125, 211, 252, 0.16);
  color: #dbeafe;
}

.carepal-page.is-dark .carepal-chat-voice-transcript-btn {
  background: rgba(230, 238, 252, 0.16);
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-chat-copy-panel {
  background: #0b1220;
  border: 1rpx solid rgba(255, 255, 255, 0.12);
}

.carepal-page.is-dark .carepal-chat-copy-title {
  color: #eaf2ff;
}

.carepal-page.is-dark .carepal-chat-copy-textarea {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(125, 211, 252, 0.28);
  color: #e6eefc;
}

.carepal-page.is-dark .carepal-schedule-edit-panel {
  background: #0b1220;
  border: 1rpx solid rgba(255, 255, 255, 0.12);
}

.carepal-page.is-dark .carepal-schedule-edit-title {
  color: #eaf2ff;
}

.carepal-page.is-dark .carepal-schedule-edit-subtitle {
  color: rgba(230, 238, 252, 0.74);
}

.carepal-page.is-dark .carepal-schedule-edit-input {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(125, 211, 252, 0.28);
  color: #e6eefc;
}

.carepal-weekly-page-tab-btn.is-active {
  border-color: rgba(141, 194, 255, 0.56);
  box-shadow: 0 10rpx 20rpx rgba(127, 174, 226, 0.24);
}

.carepal-weekly-page-head {
  margin-top: 12rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12rpx;
}

.carepal-weekly-page-title {
  font-size: 34rpx;
  color: var(--cp-text-primary);
  font-weight: 600;
}

.carepal-weekly-page-index {
  font-size: 28rpx;
  color: var(--cp-text-muted);
}

.carepal-weekly-page-actions {
  margin-top: 10rpx;
  display: flex;
  justify-content: flex-end;
  gap: 8rpx;
}

.carepal-weekly-page-action-btn {
  min-height: 62rpx;
  border-radius: 12rpx;
}

.carepal-weekly-page-action-btn :deep(.var-button__content) {
  font-size: 28rpx;
}

.carepal-weekly-score-item {
  border-radius: 12rpx;
  border: 1rpx solid rgba(80, 122, 197, 0.16);
  background: rgba(255, 255, 255, 0.72);
  padding: 12rpx;
}

.carepal-weekly-score-title {
  font-size: 36rpx;
  color: var(--cp-text-primary);
  font-weight: 600;
}

.carepal-weekly-score-prompt {
  margin-top: 6rpx;
  font-size: 32rpx;
  color: var(--cp-text-muted);
  line-height: 1.55;
}

.carepal-weekly-score-options {
  margin-top: 10rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.carepal-weekly-score-btn {
  min-width: 138rpx;
  height: 74rpx;
  border: 1rpx solid rgba(150, 203, 255, 0.26);
  box-shadow: 0 4rpx 12rpx rgba(146, 181, 224, 0.1);
}

.carepal-weekly-score-btn :deep(.var-button__content) {
  font-size: 30rpx;
}

.carepal-weekly-score-btn.is-active {
  border-color: rgba(140, 193, 255, 0.58);
  box-shadow: 0 10rpx 18rpx rgba(127, 176, 228, 0.24);
}

.carepal-weekly-score-desc {
  margin-top: 8rpx;
  font-size: 32rpx;
  color: var(--cp-text-secondary);
}

.carepal-weekly-form-item {
  margin-top: 10rpx;
}

.carepal-weekly-auto-week {
  margin-top: 6rpx;
  border-radius: 12rpx;
  padding: 10rpx 12rpx;
  font-size: 28rpx;
  color: var(--cp-text-primary);
  background: linear-gradient(135deg, rgba(76, 157, 255, 0.12) 0%, rgba(60, 211, 193, 0.1) 100%);
  border: 1rpx solid rgba(76, 157, 255, 0.22);
}

.carepal-weekly-score-legend {
  margin-top: 12rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.82);
  border: 1rpx solid rgba(80, 122, 197, 0.18);
  padding: 14rpx;
}

.carepal-weekly-voice-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12rpx;
}

.carepal-weekly-voice-badge {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: #0f3f77;
  background: linear-gradient(135deg, rgba(118, 202, 255, 0.5) 0%, rgba(124, 239, 220, 0.5) 100%);
  border: 1rpx solid rgba(76, 157, 255, 0.32);
}

.carepal-weekly-legend-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 30rpx;
  color: var(--cp-text-secondary);
  line-height: 1.6;
  margin-top: 6rpx;
}

.carepal-weekly-legend-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  flex: 0 0 auto;
}

.carepal-weekly-legend-dot.is-0 { background: #22c55e; }
.carepal-weekly-legend-dot.is-1 { background: #84cc16; }
.carepal-weekly-legend-dot.is-2 { background: #f59e0b; }
.carepal-weekly-legend-dot.is-3 { background: #f97316; }
.carepal-weekly-legend-dot.is-4 { background: #ef4444; }

.carepal-weekly-voice-stage {
  margin-top: 10rpx;
  border-radius: 16rpx;
  background: rgba(255, 255, 255, 0.85);
  border: 1rpx solid rgba(80, 122, 197, 0.18);
  padding: 16rpx;
}

.carepal-weekly-score-chip {
  border-radius: 999rpx;
  padding: 6rpx 12rpx;
  font-size: 22rpx;
  color: var(--cp-text-secondary);
  background: rgba(76, 157, 255, 0.1);
  border: 1rpx solid rgba(76, 157, 255, 0.16);
}

.carepal-weekly-voice-actions {
  margin-top: 10rpx;
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
}

.carepal-weekly-voice-actions--large {
  gap: 14rpx;
}

.carepal-weekly-label {
  font-size: 34rpx;
  color: var(--cp-text-secondary);
  margin-bottom: 6rpx;
}

.carepal-weekly-textarea {
  width: 100%;
  min-height: 176rpx;
  border-radius: 12rpx;
  border: 1rpx solid rgba(80, 122, 197, 0.22);
  background: var(--cp-surface-lv3);
  box-sizing: border-box;
  padding: 12rpx;
  font-size: 34rpx;
  color: var(--cp-text-secondary);
}

.carepal-weekly-result-text {
  white-space: pre-line;
  font-size: 34rpx;
  color: var(--cp-text-secondary);
  line-height: 1.7;
}

.carepal-weekly-result-encouragement {
  margin-top: 14rpx;
  padding-top: 10rpx;
  border-top: 1rpx solid rgba(80, 122, 197, 0.16);
  white-space: pre-line;
  font-size: 44rpx;
  line-height: 1.7;
  font-weight: 700;
  color: var(--cp-text-primary);
}

.carepal-page.is-dark .carepal-weekly-card,
.carepal-page.is-dark .carepal-weekly-result {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.16);
}

.carepal-page.is-dark .carepal-weekly-card--hero {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.24) 0%, rgba(45, 212, 191, 0.2) 100%);
  border-color: rgba(125, 211, 252, 0.36);
}

.carepal-page.is-dark .carepal-weekly-card--voice {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.12) 0%, rgba(30, 41, 59, 0.32) 100%);
}

.carepal-page.is-dark .carepal-weekly-textarea {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.2);
  color: rgba(241, 245, 255, 0.9);
}

.carepal-page.is-dark .carepal-weekly-score-item {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.18);
}

.carepal-page.is-dark .carepal-weekly-result-encouragement {
  border-top-color: rgba(255, 255, 255, 0.2);
  color: rgba(241, 245, 255, 0.95);
}

.carepal-page.is-dark .carepal-weekly-auto-week,
.carepal-page.is-dark .carepal-weekly-voice-stage {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.carepal-page.is-dark .carepal-weekly-voice-badge {
  color: #e6f3ff;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.42) 0%, rgba(20, 184, 166, 0.38) 100%);
  border-color: rgba(125, 211, 252, 0.44);
}

.carepal-page.is-dark .carepal-weekly-score-legend,
.carepal-page.is-dark .carepal-weekly-card--voice,
.carepal-page.is-dark .carepal-weekly-score-list,
.carepal-page.is-dark .carepal-weekly-score-item {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.18);
}

.carepal-page.is-dark .carepal-weekly-score-chip {
  background: rgba(125, 211, 252, 0.16);
  border-color: rgba(125, 211, 252, 0.26);
}

.carepal-page.is-dark .carepal-weekly-page-title {
  color: rgba(241, 245, 255, 0.94);
}

.carepal-page.is-dark .carepal-weekly-page-index {
  color: rgba(230, 238, 252, 0.78);
}

.carepal-page.is-dark .carepal-weekly-page-tab-btn,
.carepal-page.is-dark .carepal-weekly-score-btn {
  border-color: rgba(186, 230, 253, 0.26);
  box-shadow: 0 6rpx 16rpx rgba(0, 0, 0, 0.2);
}

.carepal-page.is-dark .carepal-weekly-page-tab-btn.is-active,
.carepal-page.is-dark .carepal-weekly-score-btn.is-active {
  border-color: rgba(186, 230, 253, 0.52);
  box-shadow: 0 10rpx 22rpx rgba(125, 211, 252, 0.2);
}
.carepal-page.is-dark .carepal-calendar-drawer {
  background: linear-gradient(180deg, rgba(20, 29, 48, 0.98) 0%, rgba(11, 16, 28, 0.98) 100%);
  border-left-color: rgba(186, 230, 253, 0.24);
  box-shadow: -22rpx 0 50rpx rgba(0, 0, 0, 0.42);
}
.carepal-page.is-dark .carepal-calendar-drawer-header {
  border-bottom-color: rgba(147, 197, 253, 0.28);
}


@media screen and (max-width: 900px) {
  .carepal-ocr-layout {
    flex-direction: column;
  }
}

/* 我的 / 设置样式 */
.carepal-profile-section {
  margin-top: 16rpx;
  padding-top: 10rpx;
  border-top: 1rpx solid #eef0f6;
}

/* 基础设置更紧凑一些 */
.carepal-profile-section--basic {
  margin-top: 10rpx;
  padding-top: 6rpx;
}

.carepal-profile-section--basic .carepal-profile-title {
  margin-bottom: 16rpx;
}

.carepal-profile-section--basic .carepal-profile-row {
  padding: 10rpx 0;
}

.carepal-profile-section--basic .carepal-profile-row + .carepal-profile-row {
  margin-top: 10rpx;
}

.carepal-profile-title {
  font-size: 38rpx;
  font-weight: 500;
  color: #233a60;
  margin-bottom: 8rpx;
}

.carepal-profile-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8rpx 0;
}

/* 仅加大“名字/手机号”两行之间的间距 */
.carepal-profile-row--form + .carepal-profile-row--form {
  margin-top: 20rpx;
}

.carepal-profile-label {
  font-size: 34rpx;
  color: #4b5875;
}

.carepal-profile-value {
  font-size: 34rpx;
  color: #202742;
}

/* “我们”模块输入框字号提升（Varlet Input 内部 input 需要 deep 覆盖） */
.carepal-profile :deep(.var-input__input) {
  font-size: 34rpx;
}

.carepal-profile :deep(.var-input__placeholder) {
  font-size: 34rpx;
}

.carepal-profile-control {
  display: flex;
  align-items: center;
}

.carepal-profile-row--avatar {
  align-items: center;
}

.carepal-profile-control--avatar {
  gap: 16rpx;
}

.carepal-profile-avatar {
  width: 86rpx;
  height: 86rpx;
  border-radius: 50%;
  background: #f0f4ff;
}

.carepal-profile-control--edit {
  flex: 1;
  justify-content: flex-end;
  gap: 12rpx;
}

.carepal-profile-control--edit :deep(.var-input) {
  width: 380rpx;
  max-width: 100%;
}

.carepal-profile-value--click {
  text-align: right;
}

.carepal-profile-actions {
  margin-top: 16rpx;
  display: flex;
  justify-content: flex-end;
}

.carepal-profile-save {
  padding: 0 32rpx;
}

.carepal-chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: var(--cp-surface-lv1);
  border-radius: 24rpx;
  box-shadow: 0 24rpx 56rpx rgba(17, 38, 92, 0.14);
  border: 1rpx solid rgba(18, 48, 85, 0.06);
  padding: 24rpx 24rpx 10rpx;
  box-sizing: border-box;
}

.carepal-chat-header {
  margin-bottom: 16rpx;
}

.carepal-chat-title {
  font-size: 36rpx;
  font-weight: 600;
  color: #123055;
  margin-bottom: 6rpx;
}

.carepal-chat-status {
  font-size: 28rpx;
  color: #7a8499;
}

.carepal-chat-body {
  flex: 1;
  min-height: 0;
  height: 0;
  max-height: calc(100vh - 380rpx);
  background: var(--cp-surface-lv2);
  border-radius: 18rpx;
  padding: 18rpx 16rpx;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.carepal-chat-body::-webkit-scrollbar {
  width: 8px;
}

.carepal-chat-body::-webkit-scrollbar-track {
  background: rgba(112, 128, 154, 0.12);
  border-radius: 999px;
}

.carepal-chat-body::-webkit-scrollbar-thumb {
  background: rgba(76, 157, 255, 0.56);
  border-radius: 999px;
}

.carepal-chat-body::-webkit-scrollbar-thumb:hover {
  background: rgba(76, 157, 255, 0.74);
}

.carepal-chat-msg {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16rpx;
}

.carepal-chat-msg.is-ai {
  flex-direction: row;
}

.carepal-chat-msg.is-user {
  flex-direction: row-reverse;
}

.carepal-chat-avatar {
  width: 56rpx;
  height: 56rpx;
  border-radius: 50%;
  background: #4c9dff;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  margin: 0 10rpx;
}

.carepal-chat-avatar--user {
  background: #ffb347;
}

.carepal-chat-bubble {
  max-width: 100%;
  padding: 14rpx 18rpx;
  border-radius: 20rpx;
  font-size: 30rpx;
  line-height: 1.6;
}

.carepal-chat-bubble-wrap {
  display: flex;
  align-items: center;
  gap: 10rpx;
  max-width: 82%;
}

.carepal-chat-msg.is-ai .carepal-chat-bubble {
  background: #ffffff;
  color: #202742;
  box-shadow: 0 4rpx 14rpx rgba(0, 0, 0, 0.06);
}

.carepal-chat-msg.is-user .carepal-chat-bubble {
  background: #4c9dff;
  color: #ffffff;
}

.carepal-chat-tts-btn {
  width: 54rpx;
  height: 54rpx;
  border-radius: 50%;
  background: rgba(76, 157, 255, 0.16);
  color: #1e4f91;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26rpx;
  flex: 0 0 auto;
}

.carepal-chat-voice-wrap {
  max-width: 82%;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.carepal-chat-voice-bar {
  min-width: 200rpx;
  max-width: 420rpx;
  border-radius: 18rpx;
  padding: 12rpx 16rpx;
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
  background: rgba(76, 157, 255, 0.14);
  color: #123055;
}

.carepal-chat-msg.is-user .carepal-chat-voice-bar {
  background: #4c9dff;
  color: #ffffff;
}

.carepal-chat-voice-icon {
  font-size: 22rpx;
}

.carepal-chat-voice-label {
  font-size: 28rpx;
  font-weight: 600;
}

.carepal-chat-voice-text {
  font-size: 25rpx;
  color: var(--cp-text-muted);
  line-height: 1.45;
}

.carepal-chat-bubble--loading {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.carepal-chat-loading-text {
  font-size: 28rpx;
}

.carepal-chat-loading-dots {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.carepal-chat-loading-dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.35;
  animation: carepal-chat-dot-pulse 1s ease-in-out infinite;
}

.carepal-chat-loading-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.carepal-chat-loading-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes carepal-chat-dot-pulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-4rpx);
  }
}

.carepal-chat-input {
  margin-top: 16rpx;
}

.carepal-chat-mic-status {
  margin-top: 10rpx;
  padding-left: 8rpx;
  font-size: 24rpx;
  color: var(--cp-text-muted);
}

.carepal-chat-input-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.carepal-chat-input-main {
  flex: 1;
  border-radius: 999rpx;
  background: var(--cp-surface-lv3);
  padding: 0 14rpx;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  height: 86rpx;
  min-height: 86rpx;
  overflow: hidden;
}

.carepal-chat-hold-to-talk {
  flex: 1;
  height: 86rpx;
  border-radius: 999rpx;
  border: 1rpx solid rgba(76, 157, 255, 0.35);
  background: rgba(76, 157, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;
  color: #1e4f91;
  user-select: none;
}

.carepal-chat-textarea {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 100%;
  max-height: 100%;
  font-size: 28rpx;
  color: #202742;
  background: transparent;
  line-height: 1.45;
  box-sizing: border-box;
  padding: 0;
}

.carepal-chat-input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12rpx;
}

.carepal-chat-send {
  padding: 0 30rpx;
  height: 86rpx;
  border-radius: 16rpx;
}

.carepal-chat-mic {
  width: 110rpx;
  height: 110rpx;
  border-radius: 50%;
  font-size: 28rpx;
}

.carepal-login-mask {
  position: fixed;
  inset: 0;
  z-index: 120;
  background: rgba(7, 14, 30, 0.56);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  box-sizing: border-box;
}

.carepal-login-panel {
  width: min(680rpx, 100%);
  border-radius: 20rpx;
  background: #ffffff;
  padding: 22rpx;
  box-sizing: border-box;
  box-shadow: 0 20rpx 40rpx rgba(0, 0, 0, 0.22);
}

.carepal-login-tabs {
  display: flex;
  gap: 12rpx;
  margin-bottom: 14rpx;
}

.carepal-login-tab-btn {
  flex: 1;
}

.carepal-login-title {
  font-size: 34rpx;
  font-weight: 600;
  color: #123055;
}

.carepal-login-subtitle {
  margin-top: 6rpx;
  margin-bottom: 14rpx;
  font-size: 24rpx;
  color: var(--cp-text-muted);
}

.carepal-login-input {
  margin-bottom: 12rpx;
}

.carepal-login-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
  margin-top: 8rpx;
}

.carepal-login-btn {
  min-width: 120rpx;
}

.carepal-login-btn--danger {
  color: #d93025;
  border-color: rgba(217, 48, 37, 0.36);
}

.carepal-page.is-dark .carepal-login-panel {
  background: #0d1526;
  border: 1rpx solid rgba(255, 255, 255, 0.12);
}

.carepal-page.is-dark .carepal-login-title {
  color: rgba(241, 245, 255, 0.94);
}

/* 模块切换动效 */
.carepal-module-stage {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
}

.carepal-module-enter-active,
.carepal-module-leave-active {
  transition: opacity 0.26s ease, transform 0.26s ease;
}

.carepal-module-enter-from,
.carepal-module-leave-to {
  opacity: 0;
  transform: translateY(8rpx);
}

/* 统一过渡，暗夜/浅色切换更平滑 */
.carepal-sidebar,
.carepal-panel,
.carepal-chat,
.carepal-header,
.carepal-chat-input-main,
.carepal-ocr-drop,
.carepal-ocr-explain,
.carepal-ocr-explain-body,
.carepal-table,
.carepal-table-row,
.carepal-table-head,
.carepal-nav-button {
  transition: background var(--cp-motion-mid) ease, color var(--cp-motion-mid) ease, border-color var(--cp-motion-mid) ease, box-shadow var(--cp-motion-mid) ease, transform var(--cp-motion-fast) ease;
}

/* Web 端 hover 反馈 */
@media (hover: hover) and (pointer: fine) {
  .carepal-nav-button,
  .carepal-chat-send,
  .carepal-chat-mic,
  .carepal-profile-btn,
  .carepal-profile-save,
  .carepal-ocr-drop {
    cursor: pointer;
  }

  .carepal-nav-button:hover {
    transform: translateY(-2rpx);
    box-shadow: 0 12rpx 24rpx rgba(24, 68, 150, 0.2);
    border-color: rgba(76, 157, 255, 0.32);
  }

  .carepal-page.is-dark .carepal-nav-button:hover {
    box-shadow: 0 12rpx 26rpx rgba(0, 0, 0, 0.35);
    border-color: rgba(125, 211, 252, 0.4);
  }

  .carepal-table-row:hover {
    background: rgba(76, 157, 255, 0.12);
  }

  .carepal-page.is-dark .carepal-table-row:hover {
    background: rgba(255, 255, 255, 0.12);
  }

  .carepal-ocr-drop:hover {
    border-color: #4c9dff;
    background: #eef4ff;
  }

  .carepal-page.is-dark .carepal-ocr-drop:hover {
    border-color: rgba(99, 179, 255, 0.9);
    background: rgba(255, 255, 255, 0.12);
  }

  .carepal-calendar-cell:not(.is-empty):hover {
    transform: translateY(-1rpx);
    border-color: rgba(76, 157, 255, 0.48);
    box-shadow: 0 4rpx 10rpx rgba(76, 157, 255, 0.14);
  }

  .carepal-page.is-dark .carepal-calendar-cell:not(.is-empty):hover {
    border-color: rgba(125, 211, 252, 0.58);
    box-shadow: 0 4rpx 10rpx rgba(125, 211, 252, 0.18);
  }

  .carepal-chat-send:hover,
  .carepal-chat-mic:hover,
  .carepal-profile-btn:hover,
  .carepal-profile-save:hover {
    filter: brightness(1.04);
    transform: translateY(-1rpx);
  }
}

/* Web 端滚动条美化 */
.carepal-page ::-webkit-scrollbar {
  width: 10rpx;
  height: 10rpx;
}

.carepal-page ::-webkit-scrollbar-track {
  background: rgba(20, 49, 93, 0.08);
  border-radius: 999rpx;
}

.carepal-page ::-webkit-scrollbar-thumb {
  background: rgba(76, 157, 255, 0.45);
  border-radius: 999rpx;
}

.carepal-page ::-webkit-scrollbar-thumb:hover {
  background: rgba(76, 157, 255, 0.7);
}

.carepal-page.is-dark ::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.08);
}

.carepal-page.is-dark ::-webkit-scrollbar-thumb {
  background: rgba(148, 198, 255, 0.46);
}

.carepal-page.is-dark ::-webkit-scrollbar-thumb:hover {
  background: rgba(188, 221, 255, 0.72);
}

@media screen and (min-width: 900px) {
  .carepal-shell {
    width: 100%;
  }

  .carepal-main {
    gap: 32rpx;
  }
}

@media screen and (max-width: 900px) {
  .carepal-header {
    border-radius: 20rpx;
  }

  .carepal-header-brand {
    gap: 10rpx;
  }

  .carepal-header-logo {
    width: 48rpx;
    height: 48rpx;
    border-radius: 12rpx;
    font-size: 20rpx;
  }

  .carepal-header-subtitle {
    display: none;
  }

  .carepal-header-right {
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8rpx;
  }

  .carepal-header-chip {
    height: 48rpx;
    padding: 0 14rpx;
    font-size: 22rpx;
  }

  .carepal-header-user {
    padding: 6rpx 12rpx;
    gap: 8rpx;
  }

  .carepal-header-user-dot {
    width: 10rpx;
    height: 10rpx;
  }
}
</style>
