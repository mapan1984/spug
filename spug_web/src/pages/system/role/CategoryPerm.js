/**
 * Copyright (c) OpenSpug Organization. https://github.com/openspug/spug
 * Copyright (c) <spug.dev@gmail.com>
 * Released under the AGPL-3.0 License.
 */
import React from 'react';
import { observer } from 'mobx-react';
import { Modal, Form, Transfer, message, Alert } from 'antd';
import http from 'libs/http';
import store from './store';

@observer
class CategoryPerm extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      loading: false,
      categories: [],
    }
  }

  componentDidMount() {
    http.get('/api/host/category/')
      .then(res => {
        const categories = res.categories.map(c => {
          return {...c, key: c.id}
        })
        this.setState({categories})
      })
  }

  handleSubmit = () => {
    this.setState({loading: true});
    http.patch('/api/account/role/', {id: store.record.id, category_perms: store.categoryPerms})
      .then(res => {
        message.success('操作成功');
        store.categoryPermVisible = false;
        store.fetchRecords();
      }, () => this.setState({loading: false}))
  }

  handleChange = (nextTargetKeys, direction, moveKeys) => {
    store.categoryPerms = nextTargetKeys
  };

  render() {
    return (
      <Modal
        visible
        width={800}
        maskClosable={false}
        title="主机类别权限设置"
        onCancel={() => store.categoryPermVisible = false}
        confirmLoading={this.state.loading}
        onOk={this.handleSubmit}>
        <Alert
          closable
          showIcon
          type="info"
          message="小提示"
          style={{width: 600, margin: '0 auto 20px', color: '#31708f !important'}}
          description="主机类别权限将全局影响属于该角色的用户能够看到的主机。"/>
        <Form.Item label="设置可访问的主机类别" style={{padding: '0 20px'}}>
          <Transfer
            showSearch
            listStyle={{width: 325, maxHeight: 500, minHeight: 300}}
            titles={['所有主机类别', '已选主机类别']}
            dataSource={this.state.categories}
            targetKeys={store.categoryPerms}
            onChange={this.handleChange}
            filterOption={(inputValue, option) => `${option.full_path}`.toLowerCase().indexOf(inputValue.toLowerCase()) > -1}
            render={item => `${item.full_path}`}/>
        </Form.Item>
      </Modal>
    )
  }
}

export default CategoryPerm
