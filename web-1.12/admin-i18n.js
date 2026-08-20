(function (global) {
  'use strict';

  var DEFAULT_LOCALE = 'en';
  var FALLBACK_LOCALE = 'en';
  var PREFERENCE_KEY = 'eaglerx_admin_locale';
  var hasOwn = Object.prototype.hasOwnProperty;
  var missingKeys = Object.create(null);
  var activeLocale = DEFAULT_LOCALE;
  var en = {
    'document.title': 'EaglercraftX Admin', 'accessibility.skipLink': 'Skip to main content', 'accessibility.navigation': 'Admin navigation', 'accessibility.workspace': 'Server controls and status',
    'header.title': 'EaglercraftX Console', 'header.subtitle': 'Server command center', 'header.disconnected': 'Disconnected', 'header.logout': 'Sign out',
    'nav.overview': 'Overview', 'nav.runtime': 'Runtime Control', 'nav.players': 'Player Workspace', 'nav.world': 'World Tools', 'nav.system': 'System Settings', 'nav.map': 'Map and Seed',
    'hero.eyebrow': 'Live server operations', 'hero.title': 'Keep server state in one workspace', 'hero.description': 'Review worlds, players, and TPS in one place.', 'hero.refreshPlayers': 'Refresh Players', 'hero.saveWorld': 'Save World', 'hero.loading': 'Reading server status',
    'section.status': 'Server Status', 'section.runtime': 'Runtime Control', 'section.players': 'Player Workspace', 'section.world': 'World Tools', 'section.system': 'System Settings', 'section.map': 'Map and Seed',
    'card.world': 'World Status', 'card.players': 'Online Players', 'card.tps': 'TPS', 'card.rules': 'Game Rules', 'card.config': 'Server Settings', 'card.seedmap': 'World Map',
    'action.weather': 'Weather', 'action.time': 'Time', 'action.difficulty': 'Difficulty', 'action.gamemode': 'Game Mode', 'action.playerManagement': 'Player Management', 'action.whitelist': 'Whitelist', 'action.worldTools': 'World and Teleport', 'action.commandWorkshop': 'Command Workshop', 'action.serverInfo': 'Server Information', 'action.dynmap': 'Dynmap Map',
    'option.weather.clear': 'Clear', 'option.weather.rain': 'Rain', 'option.weather.thunder': 'Thunderstorm', 'option.time': 'Sunrise, Noon, Dusk, Midnight', 'option.difficulty': 'Peaceful, Easy, Normal, Hard', 'option.gamemode': 'Survival, Creative, Adventure, Spectator', 'option.gamerules': 'Daylight cycle, weather cycle, drops, and saving',
    'field.serverConfig': 'Server announcement / MOTD', 'console.title': 'Command Terminal', 'console.placeholder': 'Enter a Minecraft / Bukkit / Paper command and press Enter...',
    'dialog.login': 'RCON Authentication', 'dialog.action': 'Quick Action', 'dialog.structure': 'Nearby Structure Results', 'dialog.playerActions': 'Player Management', 'dialog.whitelistActions': 'Whitelist Management', 'dialog.teleportActions': 'World Teleport', 'dialog.worldActions': 'World Settings', 'dialog.workshopActions': 'Command Workshop', 'dialog.broadcast': 'Server Broadcast', 'dialog.stop': 'Stop Server', 'dialog.restart': 'Restart Minecraft Service',
    'status.connection': 'Connected, awaiting authentication, or offline', 'status.heroPulse': 'RCON is ready; {players} players online; TPS {tps}', 'status.authentication': 'Enter your password to continue', 'status.players': 'No players online', 'status.tps': 'Could not load TPS', 'status.world': 'Could not load world status', 'status.seed': 'Reading the current world seed', 'status.structure': 'Searching nearby structures',
    'validation.requiredField': 'Please complete “{name}”.', 'validation.invalidValue': 'Enter a valid value.', 'toast.clipboard': 'World seed copied.', 'toast.configuration': 'Configuration saved; restart to apply.', 'console.clientPrefix': 'Request failed: {message}'
  };
  var zhCN = {
    'document.title': 'EaglercraftX 管理面板', 'accessibility.skipLink': '跳到主要内容', 'accessibility.navigation': '管理台导航', 'accessibility.workspace': '服务器控制与状态',
    'header.title': 'EaglercraftX 管理台', 'header.subtitle': '服务器命令中心', 'header.disconnected': '未连接', 'header.logout': '退出登录',
    'nav.overview': '总览', 'nav.runtime': '运行控制', 'nav.players': '玩家工作区', 'nav.world': '世界工具', 'nav.system': '系统设置', 'nav.map': '地图与种子',
    'hero.eyebrow': '服务器在线运行控制', 'hero.title': '把服务器状态，收进一个工作台', 'hero.description': '从一处查看世界、玩家与 TPS。', 'hero.refreshPlayers': '刷新玩家', 'hero.saveWorld': '保存世界', 'hero.loading': '正在读取服务器状态',
    'section.status': '服务器状态', 'section.runtime': '运行控制', 'section.players': '玩家工作区', 'section.world': '世界工具', 'section.system': '系统设置', 'section.map': '地图与种子',
    'card.world': '世界状态', 'card.players': '在线玩家', 'card.tps': 'TPS', 'card.rules': '游戏规则', 'card.config': '服务器设置', 'card.seedmap': '世界地图',
    'action.weather': '天气', 'action.time': '时间', 'action.difficulty': '难度', 'action.gamemode': '游戏模式', 'action.playerManagement': '玩家管理', 'action.whitelist': '白名单', 'action.worldTools': '世界与传送', 'action.commandWorkshop': '命令工坊', 'action.serverInfo': '服务器信息', 'action.dynmap': 'Dynmap 地图',
    'option.weather.clear': '晴天', 'option.weather.rain': '下雨', 'option.weather.thunder': '雷暴', 'option.time': '日出、正午、黄昏、午夜', 'option.difficulty': '和平、简单、普通、困难', 'option.gamemode': '生存、创造、冒险、旁观', 'option.gamerules': '昼夜、天气、掉落和自动保存',
    'field.serverConfig': '服务器公告 / MOTD', 'console.title': '命令终端', 'console.placeholder': '输入 Minecraft / Bukkit / Paper 命令，回车发送...',
    'dialog.login': 'RCON 认证', 'dialog.action': '快捷操作', 'dialog.structure': '附近结构结果', 'dialog.playerActions': '玩家管理', 'dialog.whitelistActions': '白名单管理', 'dialog.teleportActions': '世界传送', 'dialog.worldActions': '世界设置', 'dialog.workshopActions': '命令工坊', 'dialog.broadcast': '服务器广播', 'dialog.stop': '关闭服务器', 'dialog.restart': '重启 Minecraft 服务',
    'status.connection': '已连接、待认证或离线', 'status.heroPulse': 'RCON 已就绪；{players} 名玩家在线；TPS {tps}', 'status.authentication': '请输入密码后继续', 'status.players': '暂无在线玩家', 'status.tps': '读取 TPS 失败', 'status.world': '读取世界状态失败', 'status.seed': '正在读取当前世界种子', 'status.structure': '正在搜索附近结构',
    'validation.requiredField': '请填写“{name}”。', 'validation.invalidValue': '请输入有效值。', 'toast.clipboard': '世界种子已复制。', 'toast.configuration': '配置已保存，重启后生效。', 'console.clientPrefix': '请求失败：{message}'
  };
  var locales = {
    en: { id: 'en', label: 'English', messages: en },
    'zh-CN': { id: 'zh-CN', label: '简体中文', messages: zhCN }
  };

  function setLocale(localeId) {
    activeLocale = hasOwn.call(locales, localeId) ? localeId : DEFAULT_LOCALE;
    return activeLocale;
  }

  function interpolate(value, namedParams) {
    if (!namedParams) return value;
    return value.replace(/\{([A-Za-z][\w.-]*)\}/g, function (_, name) {
      return String(namedParams[name]);
    });
  }

  function t(key, namedParams) {
    var current = locales[activeLocale].messages;
    var fallback = locales[FALLBACK_LOCALE].messages;
    var value = hasOwn.call(current, key) ? current[key] : fallback[key];
    if (typeof value === 'undefined') {
      if (!missingKeys[key]) {
        missingKeys[key] = true;
        global.console.warn('[EaglerX i18n] missing key: ' + key);
      }
      return '[[missing:' + key + ']]';
    }
    return interpolate(value, namedParams);
  }

  global.EaglerXI18n = {
    DEFAULT_LOCALE: DEFAULT_LOCALE,
    FALLBACK_LOCALE: FALLBACK_LOCALE,
    PREFERENCE_KEY: PREFERENCE_KEY,
    locales: locales,
    getLocale: function () { return activeLocale; },
    setLocale: setLocale,
    t: t
  };
}(window));
