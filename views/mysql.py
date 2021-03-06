# coding=utf-8
import json
from flask.views import MethodView
from flask import render_template, Blueprint, redirect, url_for, session, request, current_app, jsonify
from common.request_get_more_values import request_get_values
from common.tail_font_log import FrontLogs
from modles.database import Mysql
from common.analysis_params import AnalysisParams
from common.connect_sql.connect_mysql import ConnMysql
from app import db
from modles.variables import Variables

mysql_blueprint = Blueprint('mysql_blueprint', __name__)


class MysqlAdd(MethodView):

    def get(self):
        return render_template('database/mysql_add.html')

    def post(self):
        user_id = session.get('user_id')
        name, ip, port, user, password, db_name, description = request_get_values(
            'name', 'ip', 'port', 'user', 'password', 'db_name', 'description')
        mysql = Mysql(name, ip, port, user, password, db_name, description, user_id)
        db.session.add(mysql)
        db.session.commit()
        FrontLogs('添加mysql配置 name: %s 成功' % name).add_to_front_log()
        return redirect(url_for('mysql_blueprint.mysql_list'))


class MysqlUpdate(MethodView):

    def get(self):
        mysql_id = request_get_values('mysql_id')
        mysql = Mysql.query.get(mysql_id)
        FrontLogs('进入编辑mysql配置 name: %s 页面' % mysql.name).add_to_front_log()
        return render_template('database/mysql_update.html', mysql=mysql)

    def post(self):
        mysql_id, name, ip, port, user, password, db_name, description = request_get_values(
            'mysql_id', 'name', 'ip', 'port', 'user', 'password', 'db_name', 'description')
        mysql = Mysql.query.get(mysql_id)
        mysql.name = name
        mysql.ip = ip
        mysql.port = port
        mysql.user =user
        mysql.password = password
        mysql.db_name = db_name
        mysql.description = description

        db.session.commit()
        FrontLogs('编辑mysql配置 name: %s 成功' % name).add_to_front_log()
        return redirect(url_for('mysql_blueprint.mysql_list'))


class MysqlList(MethodView):
    def get(self):
        user_id = session.get('user_id')
        mysql_search = request_get_values('mysql_search')
        page = request.args.get('page', 1, type=int)
        FrontLogs('进入mysql配置列表页面 第%s页' % page).add_to_front_log()
        #  pagination是salalchemy的方法，第一个参数：当前页数，per_pages：显示多少条内容 error_out:True 请求页数超出范围返回404错误 False：反之返回一个空列表
        pagination = Mysql.query.filter(Mysql.name.like(
                "%"+mysql_search+"%") if mysql_search is not None else "", Mysql.user_id == user_id). \
            order_by(Mysql.timestamp.desc()).paginate(
            page, per_page=current_app.config['FLASK_POST_PRE_ARGV'], error_out=False)
        # 返回一个内容对象
        mysqls = pagination.items
        for mysql in mysqls:
            mysql.ip, mysql.port, mysql.name, mysql.user, mysql.password = AnalysisParams().analysis_more_params(
                mysql.ip, mysql.port, mysql.name, mysql.user, mysql.password
            )
        return render_template('database/mysql_list.html', pagination=pagination, mysqls=mysqls)


def mysqlrun(mysql_id=None, sql='', regist_variable='', is_request=True):
    print('MysqlRun:', sql, regist_variable)
    mysql = Mysql.query.get(mysql_id)
    host, port, db_name, user, password = AnalysisParams().analysis_more_params(
        mysql.ip, mysql.port, mysql.db_name, mysql.user, mysql.password)
    try:
        result = ConnMysql(host, int(port), user, password, db_name, sql).select_mysql()
        if regist_variable:
            if Variables.query.filter(Variables.name == regist_variable).count() > 0:
                Variables.query.filter(Variables.name == regist_variable).first().value = str(result)
            else:
                variable = Variables(regist_variable, str(result), is_private=1, user_id=session.get('user_id'))
                db.session.add(variable)
            db.session.commit()
            if is_request:
                result = '【查询结果】<br>' + str(result) + '<br>【注册变量名】 【' + regist_variable + '】<br>' + str(result)
            else:
                return result
        else:
            result = '【查询结果】<br>' + str(result) + '<br>【未注册变量】'
        return json.dumps(result)
    except Exception as e:
        print(e)
        return json.dumps(str(e))


class MysqlRun(MethodView):

    def post(self):
        mysql_id, sql, regist_variable = request_get_values('mysql_id', 'sql', 'regist_variable')
        result = mysqlrun(mysql_id, sql, regist_variable)
        return result


class MysqlDelete(MethodView):

    def get(self):
        mysql_id = request_get_values('mysql_id')
        mysql = Mysql.query.get(mysql_id)
        db.session.delete(mysql)
        db.session.commit()
        FrontLogs('删除mysql配置 name: %s 成功' % mysql.name).add_to_front_log()
        return redirect(url_for('mysql_blueprint.mysql_list'))


class MysqlNameValidate(MethodView):

    def get(self):
        user_id = session.get('user_id')
        name = request.args.get('name')
        mysql = Mysql.query.filter(Mysql.name == name, Mysql.user_id == user_id).count()
        if mysql != 0:
            return jsonify(False)
        else:
            return jsonify(True)


class MysqlNameUpdateValidate(MethodView):

    def get(self):
        user_id = session.get('user_id')
        name, mysql_id = request_get_values('name', 'mysql_id')
        print('MysqlNameUpdateValidate:', name, mysql_id)
        mysql = Mysql.query.filter(Mysql.id != mysql_id, Mysql.name == name, Mysql.user_id == user_id).count()
        if mysql != 0:
            return jsonify(False)
        else:
            return jsonify(True)


mysql_blueprint.add_url_rule('/mysql_add/', view_func=MysqlAdd.as_view('mysql_add'))
mysql_blueprint.add_url_rule('/mysql_update/', view_func=MysqlUpdate.as_view('mysql_update'))
mysql_blueprint.add_url_rule('/mysql_list/', view_func=MysqlList.as_view('mysql_list'))
mysql_blueprint.add_url_rule('/mysql_delete/', view_func=MysqlDelete.as_view('mysql_delete'))

mysql_blueprint.add_url_rule('/mysql_run/', view_func=MysqlRun.as_view('mysql_run'))

mysql_blueprint.add_url_rule('/mysql_name_validate/', view_func=MysqlNameValidate.as_view('mysql_name_validate'))
mysql_blueprint.add_url_rule('/mysql_name_update_validate/', view_func=MysqlNameUpdateValidate.as_view('mysql_name_update_validate'))
