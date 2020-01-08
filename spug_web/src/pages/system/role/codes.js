export default [{
  key: 'host',
  label: '主机管理',
  pages: [{
    key: 'host',
    label: '主机管理',
    perms: [
      {key: 'view', label: '查看主机'},
      {key: 'add', label: '新建主机'},
      {key: 'edit', label: '编辑主机'},
      {key: 'del', label: '删除主机'},
      {key: 'console', label: 'Console'},
    ]
  }]
}, {
  key: 'exec',
  label: '批量执行',
  pages: [{
    key: 'task',
    label: '执行任务',
    perms: [
      {key: 'do', label: '执行任务'}
    ]
  }, {
    key: 'template',
    label: '模板管理',
    perms: [
      {key: 'view', label: '查看模板'},
      {key: 'add', label: '新建模板'},
      {key: 'edit', label: '编辑模板'},
      {key: 'del', label: '删除模板'},
    ]
  }]
}, {
  key: 'deploy',
  label: '应用发布',
  pages: [{
    key: 'app',
    label: '应用管理',
    perms: [
      {key: 'view', label: '查看应用'},
      {key: 'add', label: '新建应用'},
      {key: 'edit', label: '编辑应用'},
      {key: 'del', label: '删除应用'},
    ]
  }, {
    key: 'request',
    label: '发布申请',
    perms: [
      {key: 'view', label: '查看申请'},
      {key: 'add', label: '新建申请'},
      {key: 'edit', label: '编辑申请'},
      {key: 'del', label: '删除申请'},
      {key: 'do', label: '执行发布'}
    ]
  }]
}, {
  key: 'schedule',
  label: '任务计划',
  pages: [{
    key: 'schedule',
    label: '任务计划',
    perms: [
      {key: 'view', label: '查看任务'},
      {key: 'add', label: '新建任务'},
      {key: 'edit', label: '编辑任务'},
      {key: 'del', label: '删除任务'},
    ]
  }]
}, {
  key: 'config',
  label: '配置中心',
  pages: [{
    key: 'env',
    label: '环境管理',
    perms: [
      {key: 'view', label: '查看环境'},
      {key: 'add', label: '新建环境'},
      {key: 'edit', label: '编辑环境'},
      {key: 'del', label: '删除环境'}
    ]
  }, {
    key: 'service',
    label: '服务管理',
    perms: [
      {key: 'view', label: '查看服务'},
      {key: 'add', label: '新建服务'},
      {key: 'edit', label: '编辑服务'},
      {key: 'del', label: '删除服务'},
      {key: 'view_config', label: '查看配置'},
      {key: 'edit_config', label: '修改配置'},
    ]
  }, {
    key: 'app',
    label: '应用管理',
    perms: [
      {key: 'view', label: '查看应用'},
      {key: 'add', label: '新建应用'},
      {key: 'edit', label: '编辑应用'},
      {key: 'del', label: '删除应用'},
      {key: 'view_config', label: '查看配置'},
      {key: 'edit_config', label: '修改配置'},
    ]
  }]
}]