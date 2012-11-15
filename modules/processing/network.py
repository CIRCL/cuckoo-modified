# Copyright (C) 2010-2012 Cuckoo Sandbox Developers.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import os
import re
import sys
import socket
import logging
from urlparse import urlunparse

from lib.cuckoo.common.utils import convert_to_printable
from lib.cuckoo.common.abstracts import Processing
from lib.cuckoo.common.config import Config

try:
    import dpkt
    IS_DPKT = True
except ImportError:
    IS_DPKT = False

class Pcap:
    """Reads network data from PCAP file."""

    def __init__(self, filepath):
        """Creates a new instance.
        @param filepath: path to PCAP file
        """
        self.filepath = filepath

        # List containing all IP addresses involved in the analysis.
        self.unique_hosts = []
        # List of unique domains.
        self.unique_domains = []
        # List containing all TCP packets.
        self.tcp_connections = []
        # List containing all UDP packets.
        self.udp_connections = []
        # List containing all HTTP requests.
        self.http_requests = []
        # List containing all DNS requests.
        self.dns_requests = []
        # List containing all SMTP requests.
        self.smtp_requests = []
        # Reconstruncted SMTP flow.
        self.smtp_flow = {}
        # Dictionary containing all the results of this processing.
        self.results = {}

    def _add_hosts(self, connection):
        """Add IPs to unique list.
        @param connection: connection data
        """
        try:
            if connection["src"] not in self.unique_hosts:
                self.unique_hosts.append(convert_to_printable(connection["src"]))
            if connection["dst"] not in self.unique_hosts:
                self.unique_hosts.append(convert_to_printable(connection["dst"]))
        except Exception:
            return False

        return True

    def _dns_gethostbyname(self, name):
        """Get host by name wrapper.
        @param name: hostname.
        @return: IP address or blank
        """
        if Config().cuckoo.resolve_dns:
            try:
                socket.setdefaulttimeout(10)
                ip = socket.gethostbyname(name)
            except socket.gaierror:
                ip = ""
        else:
            ip = ""
        return ip

    def _add_domain(self, domain):
        """Add a domain to unique list.
        @param domain: domain name.
        """
        filters = [
            ".*\\.windows\\.com$",
            ".*\\.in\\-addr\\.arpa$"
        ]

        regexps = [re.compile(filter) for filter in filters]
        for regexp in regexps:
            if regexp.match(domain):
                return

        for entry in self.unique_domains:
            if entry["domain"] == domain:
                return

        self.unique_domains.append({"domain" : domain,
                                    "ip" : self._dns_gethostbyname(domain)})

    def _check_http(self, tcpdata):
        """Checks for HTTP traffic.
        @param tcpdata: TCP data flow.
        """
        try:
            dpkt.http.Request(tcpdata)
        except dpkt.dpkt.UnpackError:
            return False

        return True

    def _add_http(self, tcpdata, dport):
        """Adds an HTTP flow.
        @param tcpdata: TCP data flow.
        @param dport: destination port.
        """
        http = dpkt.http.Request(tcpdata)

        try:
            entry = {}

            if "host" in http.headers:
                entry["host"] = convert_to_printable(http.headers["host"])
            else:
                entry["host"] = ""

            entry["port"] = dport
            entry["data"] = convert_to_printable(tcpdata)
            entry["uri"] = convert_to_printable(urlunparse(("http", entry["host"], http.uri, None, None, None)))
            entry["body"] = convert_to_printable(http.body)
            entry["path"] = convert_to_printable(http.uri)

            if "user-agent" in http.headers:
                entry["user-agent"] = convert_to_printable(http.headers["user-agent"])

            entry["version"] = convert_to_printable(http.version)
            entry["method"] = convert_to_printable(http.method)

            self.http_requests.append(entry)
        except Exception:
            return False

        return True

    def _check_dns(self, udpdata):
        """Checks for DNS traffic.
        @param udpdata: UDP data flow.
        """
        try:
            dpkt.dns.DNS(udpdata)
        except:
            return False

        return True

    def _add_dns(self, udpdata):
        """Adds a DNS data flow.
        @param udpdata: UDP data flow.
        """
        dns = dpkt.dns.DNS(udpdata)

        # DNS query parsing.
        query = {}
 
        if dns.rcode == dpkt.dns.DNS_RCODE_NOERR:
            # DNS question.
            query["request"] = dns.qd[0].name
            if dns.qd[0].type == dpkt.dns.DNS_A:
                query["type"] = "A"
            if dns.qd[0].type == dpkt.dns.DNS_AAAA:    
                query["type"] = "AAAA"
            elif dns.qd[0].type == dpkt.dns.DNS_CNAME:
                query["type"] = "CNAME"
            elif dns.qd[0].type == dpkt.dns.DNS_MX:
                query["type"] = "MX"
            elif dns.qd[0].type == dpkt.dns.DNS_PTR:
                query["type"] = "PTR"
            elif dns.qd[0].type == dpkt.dns.DNS_NS:
                query["type"] = "NS"
            elif dns.qd[0].type == dpkt.dns.DNS_SOA:
                query["type"] = "SOA"
            elif dns.qd[0].type == dpkt.dns.DNS_HINFO:
                query["type"] = "HINFO"     
            elif dns.qd[0].type == dpkt.dns.DNS_TXT:
                query["type"] = "TXT"
            elif dns.qd[0].type == dpkt.dns.DNS_SRV:
                query["type"] = "SRV"

            # DNS answer.
            query["answers"] = []
            for answer in dns.an:
                ans = {}
                if answer.type == dpkt.dns.DNS_A:
                    ans["type"] = "A"
                    ans["data"] = inet_ntoa(answer.ip)
                elif answer.type == dpkt.dns.DNS_AAAA:
                    ans["type"] = "AAAA"
                    ans["data"] = inet_ntop(AF_INET6, answer.ip6)
                elif answer.type == dpkt.dns.DNS_CNAME:
                    ans["type"] = "CNAME"
                    ans["data"] = answer.cname
                elif answer.type == dpkt.dns.DNS_MX:
                    ans["type"] = "MX"
                    ans["data"] = answer.mxname
                elif answer.type == dpkt.dns.DNS_PTR:
                    ans["type"] = "PTR"
                    ans["data"] = answer.ptrname
                elif answer.type == dpkt.dns.DNS_NS:
                    ans["type"] = "NS"
                    ans["data"] = answer.nsname   
                elif answer.type == dpkt.dns.DNS_SOA:
                    ans["type"] = "SOA"
                    ans["data"] = ",".join(answer.mname,
                                           answer.rname,
                                           str(answer.serial),
                                           str(answer.refresh),
                                           str(answer.retry),
                                           str(answer.expire),
                                           str(answer.minimum)) 
                elif answer.type == dpkt.dns.DNS_HINFO:
                    ans["type"] = "HINFO"
                    ans["data"] = " ".join(answer.text)             
                elif answer.type == dpkt.dns.DNS_TXT:
                    ans["type"] = "TXT"
                    ans["data"] = " ".join(answer.text)
                # TODO: add srv handling
                query["answers"].append(ans)

            self._add_domain(query["request"])
            self.dns_requests.append(query)

        return True

    def _reassemble_smtp(self, conn, data):
        """Reassemble a SMTP flow.
        @param conn: connection dict.
        @param data: raw data.
        """
        if conn["dst"] in self.smtp_flow:
            self.smtp_flow[conn["dst"]] += data
        else:
            self.smtp_flow[conn["dst"]] = data

    def _process_smtp(self):
        """Process SMTP flow."""
        for conn, data in self.smtp_flow.iteritems():
            # Detect new SMTP flow.
            if data.startswith("EHLO") or data.startswith("HELO"):
                self.smtp_requests.append({"dst": conn, "raw": data})

    def _tcp_dissect(self, conn, data):
        """Runs all TCP dissectors.
        @param conn: connection.
        @param data: payload data.
        """
        if self._check_http(data):
            self._add_http(data, conn["dport"])
        # SMTP.
        if conn["dport"] == 25:
            self._reassemble_smtp(conn, data)

    def _udp_dissect(self, conn, data):
        """Runs all UDP dissectors.
        @param conn: connection.
        @param data: payload data.
        """
        if conn["dport"] == 53:
            if self._check_dns(data):
                self._add_dns(data)

    def run(self):
        """Process PCAP.
        @return: dict with network analysis data.
        """
        log = logging.getLogger("Processing.Pcap")

        if not IS_DPKT:
            log.error("Python DPKT is not installed, aborting PCAP analysis.")
            return None

        if not os.path.exists(self.filepath):
            log.warning("The PCAP file does not exist at path \"%s\"." % self.filepath)
            return None

        if os.path.getsize(self.filepath) == 0:
            log.error("The PCAP file at path \"%s\" is empty." % self.filepath)
            return None

        try:
            file = open(self.filepath, "rb")
        except (IOError, OSError):
            log.error("Unable to open %s" % self.filepath)
            return None

        try:
            pcap = dpkt.pcap.Reader(file)
        except dpkt.dpkt.NeedData:
            log.error("Unable to read PCAP file at path \"%s\"." % self.filepath)
            return None

        for ts, buf in pcap:
            try:
                eth = dpkt.ethernet.Ethernet(buf)
                ip = eth.data

                connection = {}
                if isinstance(ip, dpkt.ip.IP):
                    connection["src"] = socket.inet_ntoa(ip.src)
                    connection["dst"] = socket.inet_ntoa(ip.dst)
                elif isinstance(ip, dpkt.ip6.IP6):
                    connection["src"] = socket.inet_ntop(socket.AF_INET6, ip.src)
                    connection["dst"] = socket.inet_ntop(socket.AF_INET6, ip.dst)

                self._add_hosts(connection)

                if ip.p == dpkt.ip.IP_PROTO_TCP:

                    tcp = ip.data

                    if len(tcp.data) > 0:
                        connection["sport"] = tcp.sport
                        connection["dport"] = tcp.dport
                        self._tcp_dissect(connection, tcp.data)
                        self.tcp_connections.append(connection)
                    else:
                        continue
                elif ip.p == dpkt.ip.IP_PROTO_UDP:
                    udp = ip.data

                    if len(udp.data) > 0:
                        connection["sport"] = udp.sport
                        connection["dport"] = udp.dport
                        self._udp_dissect(connection, udp.data)
                        self.udp_connections.append(connection)
                #elif ip.p == dpkt.ip.IP_PROTO_ICMP:
                    #icmp = ip.data
            except AttributeError:
                continue
            except dpkt.dpkt.NeedData:
                continue

        file.close()

        # Post processors for reconstructed flows.
        self._process_smtp()

        # Build results dict.
        self.results["hosts"] = self.unique_hosts
        self.results["domains"] = self.unique_domains
        self.results["tcp"] = self.tcp_connections
        self.results["udp"] = self.udp_connections
        self.results["http"] = self.http_requests
        self.results["dns"] = self.dns_requests
        self.results["smtp"] = self.smtp_requests

        return self.results

class NetworkAnalysis(Processing):
    """Network analysis."""

    def run(self):
        self.key = "network"

        results = Pcap(self.pcap_path).run()

        return results
