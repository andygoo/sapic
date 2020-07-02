# -*- coding: utf-8 -*-
"""
    cli
    ~~~

    Cli Entrance

    :copyright: (c) 2020 by staugur.
    :license: BSD 3-Clause, see LICENSE for more details.
"""

import json
import click
from flask.cli import AppGroup
from redis.exceptions import RedisError
from werkzeug.security import generate_password_hash
from libs.storage import get_storage
from .tool import rsp, get_current_timestamp, create_redis_engine, is_true, \
    parse_ua
from .web import check_username, _pip_install


def echo(msg, color=None):
    click.echo(click.style(msg, fg=color))


def exec_createuser(username, password, **kwargs):
    """创建账号"""
    ak = rsp("accounts")
    username = username.lower()
    if check_username(username):
        if not password or len(password) < 6:
            echo("密码最少6位", "yellow")
        else:
            rc = create_redis_engine()
            if rc.sismember(ak, username):
                echo("用户名已存在", "red")
            else:
                is_admin = kwargs.pop("is_admin", 0)
                uk = rsp("account", username)
                pipe = rc.pipeline()
                pipe.sadd(ak, username)
                if kwargs:
                    pipe.hmset(uk, kwargs)
                pipe.hmset(uk, dict(
                    username=username,
                    password=generate_password_hash(password),
                    is_admin=1 if is_true(is_admin) else 0,
                    ctime=get_current_timestamp(),
                    status=1,
                ))
                try:
                    pipe.execute()
                except RedisError as e:
                    echo(e, "red")
                else:
                    echo("注册成功！", "green")
                finally:
                    rc.connection_pool.disconnect()
    else:
        echo("用户名不合法或不允许注册", "yellow")


sa_cli = AppGroup('sa', help='Administrator commands', context_settings={
                  'help_option_names': ['-h', '--help']})


@sa_cli.command()
@click.option('--username', '-u', type=str, required=True, help=u'用户名')
@click.option('--password', '-p', type=str, required=True, help=u'用户密码')
@click.option('--isAdmin/--no-isAdmin', default=False,
              help=u'是否为管理员', show_default=True)
@click.option('--avatar', '-a', type=str, default='', help=u'头像地址')
@click.option('--nickname', '-n', type=str, default='', help=u'昵称')
def create(username, password, isadmin, avatar, nickname):
    """创建账号"""
    exec_createuser(
        username,
        password,
        is_admin=isadmin,
        avatar=avatar,
        nickname=nickname,
    )


@sa_cli.command()
@click.option('--HookLoadTime/--no-HookLoadTime', default=False,
              help=u'删除钩子加载时间', show_default=True)
@click.option('--HookThirds/--no-HookThirds', default=False,
              help=u'删除已加载的第三方钩子', show_default=True)
def clean(hookloadtime, hookthirds):
    """清理系统"""
    if hookloadtime:
        s = get_storage()
        del s['hookloadtime']
    if hookthirds:
        s = get_storage()
        del s['hookthirds']


@sa_cli.command()
@click.confirmation_option(prompt=u'确定要升级更新吗？')
@click.argument('v2v', type=click.Choice(['1.6.0-1.7.0', ]))
def upgrade(v2v):
    """版本升级助手"""
    #: 处理更新版本时数据迁移、数据结构变更、其他修改
    if v2v == "1.6.0-1.7.0":
        #: 安装模块
        _pip_install("user_agents>=2.0")
        #: 更新数据
        rc = create_redis_engine()
        rls = rc.keys(rsp("report", "linktokens", "*"))
        pipe = rc.pipeline()
        for k in rls:
            data = rc.lrange(k, 0, -1)
            new = []
            is_update = False
            for d in data:
                d = json.loads(d)
                if "uap" not in d:
                    is_update = True
                    d["uap"] = parse_ua(d["agent"])
                new.append(json.dumps(d))
            if is_update:
                pipe.delete(k)
                pipe.rpush(k, *new)
        pipe.execute()
