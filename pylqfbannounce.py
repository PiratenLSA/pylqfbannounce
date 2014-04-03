#!/usr/bin/python3

import datetime
import smtplib
from io import StringIO
from email.mime.text import MIMEText

import psycopg2
from psycopg2.extras import DictCursor, DictRow

from pylqfb import LQFBIssue, LQFBInitiative


SQL = """
SELECT
    a.name AS area_name,
    ini.issue_id, ini.id, ini.name, ini.eligible, ini.rank,
    i.closed, i.fully_frozen, i.half_frozen, i.accepted, i.created
FROM
    issue i JOIN initiative ini ON i.id = ini.issue_id JOIN area a ON i.area_id = a.id
WHERE
    a.unit_id = %s AND (i.closed IS NULL OR i.closed >= %s);
"""


class LQFBAnnounce(object):
    def __init__(self, unit_id, dt, login, url):
        self.unit_id = unit_id
        self.dt = dt
        self.url = url

        self.closed = dict()
        self.voting = dict()
        self.frozen = dict()
        self.discussion = dict()
        self.new = dict()

        self.email_body = StringIO()
        self.issue = None

        self.con = psycopg2.connect(login)
        self.cur = self.con.cursor(cursor_factory=DictCursor)

        self.__sql()
        self.__create_email_body()

    @staticmethod
    def __create_issue(dict_phase, rec):
        assert isinstance(rec, DictRow)

        issue_id = rec['issue_id']

        if issue_id not in dict_phase:
            dict_phase[issue_id] = LQFBIssue(rec['issue_id'], rec['closed'], rec['fully_frozen'], rec['half_frozen'],
                                             rec['accepted'], rec['created'], rec['area_name'])

        return dict_phase[issue_id]

    def __sql(self):
        self.cur.execute(SQL, (self.unit_id, self.dt))

        for record in self.cur:
            self.issue = None

            if record['closed'] is not None:
                self.issue = LQFBAnnounce.__create_issue(self.closed, record)
            elif record['fully_frozen'] is not None:
                self.issue = LQFBAnnounce.__create_issue(self.voting, record)
            elif record['half_frozen'] is not None:
                self.issue = LQFBAnnounce.__create_issue(self.frozen, record)
            elif record['accepted'] is not None:
                self.issue = LQFBAnnounce.__create_issue(self.discussion, record)
            else:
                self.issue = LQFBAnnounce.__create_issue(self.new, record)

            assert isinstance(self.issue, LQFBIssue)
            self.issue.add_initiative(LQFBInitiative(record['id'], record['name'], record['eligible'], record['rank']))

    def __create_email_body_singletype(self, dict_phase):
        for issue in dict_phase.values():
            assert isinstance(issue, LQFBIssue)
            self.email_body.write('#{0} - {1}issue/show/{0}.html:\n'.format(issue.id, self.url))
            for ini in sorted(issue.initiatives.values(), key=lambda x: x.id):
                assert isinstance(ini, LQFBInitiative)
                self.email_body.write('-> i{} {}\n'.format(ini.id, ini.name))
            self.email_body.write('\n')

    def __create_email_body(self):
        self.email_body = StringIO()

        self.email_body.write(
            'Dies ist eine wöchentliche Zusammenfassung der derzeit laufenden Initiativen im LiquidFeedback des '
            'Landesverbands.\n\n')

        if len(self.closed) > 0:
            self.email_body.write('== Abgeschlossen (letzte Woche) ==\n')
            self.email_body.write('(sortiert nach Rang, "+" = Angenommen, "-" = Abgelehnt)\n\n')

            for issue in self.closed.values():
                assert isinstance(issue, LQFBIssue)
                self.email_body.write('#{0} - {1}issue/show/{0}.html:\n'.format(issue.id, self.url))
                for ini in sorted(issue.initiatives.values(), key=lambda x: x.rank):
                    assert isinstance(ini, LQFBInitiative)
                    self.email_body.write(
                        '-> #{} ({}): i{} {}\n'.format(ini.rank, '+' if ini.eligible else '-', ini.id, ini.name))
                self.email_body.write('\n')

        self.email_body.write('\n')

        if len(self.voting) > 0:
            self.email_body.write('== Abstimmung ==\n')
            self.__create_email_body_singletype(self.voting)

        self.email_body.write('\n')

        if len(self.voting) > 0:
            self.email_body.write('== Eingefroren ==\n')
            self.__create_email_body_singletype(self.frozen)

        self.email_body.write('\n')

        if len(self.voting) > 0:
            self.email_body.write('== Diskussion ==\n')
            self.__create_email_body_singletype(self.discussion)

        self.email_body.write('\n')

        if len(self.voting) > 0:
            self.email_body.write('== Neu ==\n')
            self.__create_email_body_singletype(self.new)

        self.email_body.write(
            '\n== Anmerkungen ==\nJedem Mitglied wird spätestens ein Monat nach Beitritt ein Invitecode zugeschickt, '
            'mit dem sich ein eigener Account im LiquidFeedback angelegt werden kann. Sollte es Probleme mit dem '
            'Zugang geben, so kann sich an die E-Mail Adresse lqfb@piraten-lsa.de gewendet werden.')

    def send_email(self, email_from, email_to):
        today = datetime.date.today()

        msg = MIMEText(self.email_body.getvalue(), 'plain', 'utf-8')
        msg['Subject'] = 'LQFB Zusammenfassung ({})'.format(today.strftime('%d.%m.%Y'))
        msg['From'] = email_from
        msg['To'] = email_to

        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()


if __name__ == '__main__':
    announce = LQFBAnnounce(1, datetime.date.today() - datetime.timedelta(days=7),
                            'dbname=liquid_feedback_lsa user=www-data', 'http://lqfb.piraten-lsa.de/lsa/')

    announce.send_email('LQFB Announce <announce@lqfb.piraten-lsa.de>', 'sachsen-anhalt_aktive@lists.piraten-lsa.de')
    #announce.send_email('LQFB Announce <announce@lqfb.piraten-lsa.de>', 'christoph.giesel@piraten-lsa.de')