import datetime
import json
import sys
import urllib.parse
import arcgis.gis
from arcgis.geoprocessing._tool import _camelCase_to_underscore


def _underscore_to_camelcase(name):
    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    c = camelcase()
    return "".join(next(c)(x) if x else "_" for x in name.split("_"))


class WorkflowManagerAdmin:
    """
    Represents a series of CRUD functions for Workflow Manager Items

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    gis                 Optional GIS. The connection to the Enterprise.
    ===============     ====================================================================
    """

    def __init__(self, gis):
        self._gis = gis
        if self._gis.users.me is None:
            raise ValueError("An authenticated `GIS` is required.")
        if not any(
            prov.itemid == "50a5f00bcc574358b15eab0e2bdadf39"
            for prov in self._gis.users.me.provisions
        ):
            raise ValueError(
                "No Workflow Manager license is available for the current user"
            )
        self._url = self._wmx_server_url[0]
        if self._url is None:
            raise ValueError("No WorkflowManager Registered with your Organization")
        if not any(
            prov.itemid == "50a5f00bcc574358b15eab0e2bdadf39"
            for prov in self._gis.users.me.provisions
        ):
            raise ValueError(
                "No Workflow Manager license is available for the current user"
            )

    @property
    def _wmx_server_url(self):
        """locates the WMX server"""
        baseurl = self._gis._portal.resturl
        res = self._gis._con.get(f"{baseurl}/portals/self/servers", {"f": "json"})
        for s in res["servers"]:
            server_functions = [
                x.strip() for x in s.get("serverFunction", "").lower().split(",")
            ]
            if "workflowmanager" in server_functions:
                self._url = s.get("url", None)
                self._private_url = s.get("adminUrl", None)
                if self._url is None:
                    raise RuntimeError("Cannot find a WorkflowManager Server")
                self._url += f"/workflow"
                self._private_url += f"/workflow"
                return self._url, self._private_url
        raise RuntimeError(
            "Unable to locate Workflow Manager Server. Please contact your ArcGIS Enterprise "
            "Administrator to ensure Workflow Manager Server is properly configured."
        )
        return None

    def create_item(self, name) -> tuple:
        """
        Creates a `Workflow Manager` schema that stores all the configuration
        information and location data in the data store on Portal. This can
        be run by any user assigned to the administrator role in Portal.

        For users that do not belong to the administrator role, the
        following privileges are required to run Create Workflow Item:

        ==================  =========================================================
        **Argument**        **Description**
        ------------------  ---------------------------------------------------------
        name                Required String. The name of the new schema.
        ==================  =========================================================

        :return:
            string (item_id)
        """

        url = "{base}/admin/createWorkflowItem?token={token}&name={name}".format(
            base=self._url, token=self._gis._con.token, name=name
        )
        params = {"name": name}
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params=params,
                try_json=False,
                add_token=False,
                json_encode=False,
                post_json=True,
            )
        )["itemId"]
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    def upgrade_item(self, item):
        """
        Upgrades an outdated Workflow Manager schema. Requires the Workflow Manager
        Advanced Administrator privilege or the Portal Admin Update Content privilege.

        ==================  =========================================================
        **Argument**        **Description**
        ------------------  ---------------------------------------------------------
        item                Required Item. The Workflow Manager Item to be upgraded
        ==================  =========================================================

        :return:
            success object

        """

        url = "{base}/admin/{id}/upgrade?token={token}".format(
            base=self._url, id=item.id, token=self._gis._con.token
        )
        return_obj = json.loads(
            self._gis._con.post(
                url, try_json=False, add_token=False, json_encode=False, post_json=True
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    def delete_item(self, item):
        """
        Delete a Workflow Manager schema. Does not delete the Workflow Manager Admin group.
        Requires the administrator or publisher role. If the user has the publisher role,
        the user must also be the owner of the item to delete.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required Item. The Workflow Manager Item to be deleted
        ===============     ====================================================================

        :return:
            success object

        """

        url = "{base}/admin/{id}?token={token}".format(
            base=self._url, id=item.id, token=self._gis._con.token
        )

        return_obj = json.loads(
            self._gis._con.delete(url, add_token=False, try_json=False)
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    @property
    def server_status(self):
        """
        Gets the current status of the Workflow Manager Server

        :return:
            boolean

        """

        url = "{base}/checkStatus?token={token}".format(
            base=self._url, token=self._gis._con.token
        )

        return_obj = self._gis._con.get(url)
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    @property
    def health_check(self):
        """
        Checks the health of Workflow Manager Server and if the cluster is active (if applicable).

        :return:
            boolean

        """

        url = "{base}/healthCheck".format(base=self._url)

        return_obj = self._gis._con.get(url)
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj


class JobManager:
    """
    Represents a helper class for workflow manager jobs. Accessible as the
    :attr:`~arcgis.gis.workflowmanager.WorkflowManager.jobs` property of the
    :class:`~arcgis.gis.workflowmanager.WorkflowManager`.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    item                The Workflow Manager Item
    ===============     ====================================================================

    """

    def __init__(self, item):
        """initializer"""
        if item is None:
            raise ValueError("Item cannot be None")
        self._item = item
        self._gis = item._gis
        if self._gis.users.me is None:
            raise ValueError("An authenticated `GIS` is required.")

        self._url = self._wmx_server_url[0]
        if self._url is None:
            raise ValueError("No WorkflowManager Registered with your Organization")
        if not any(
            prov.itemid == "50a5f00bcc574358b15eab0e2bdadf39"
            for prov in self._gis.users.me.provisions
        ):
            raise ValueError(
                "No Workflow Manager license is available for the current user"
            )

    def _handle_error(self, info):
        """Basic error handler - separated into a function to allow for expansion in future releases"""
        error_class = info[0]
        error_text = info[1]
        raise Exception(error_text)

    @property
    def _wmx_server_url(self):
        """locates the WMX server"""
        baseurl = self._gis._portal.resturl
        res = self._gis._con.get(f"{baseurl}/portals/self/servers", {"f": "json"})
        for s in res["servers"]:
            server_functions = [
                x.strip() for x in s.get("serverFunction", "").lower().split(",")
            ]
            if "workflowmanager" in server_functions:
                self._url = s.get("url", None)
                self._private_url = s.get("adminUrl", None)
                if self._url is None:
                    raise RuntimeError("Cannot find a WorkflowManager Server")
                self._url += f"/workflow/{self._item.id}"
                self._private_url += f"/workflow/{self._item.id}"
                return self._url, self._private_url
        raise RuntimeError(
            "Unable to locate Workflow Manager Server. Please contact your ArcGIS Enterprise "
            "Administrator to ensure Workflow Manager Server is properly configured."
        )
        return None

    def close(self, job_ids):
        """
        Closes a single or multiple jobs with specific Job IDs

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_ids             Required list of job ID strings
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/jobs/manage?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
            return Job.manage_jobs(self._gis, url, job_ids, "Close")
        except:
            self._handle_error(sys.exc_info())

    def reopen(self, job_ids):
        """
        Reopens a single or multiple jobs with specific Job IDs

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_ids             Required list of job ID strings
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/jobs/manage?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
            return Job.manage_jobs(self._gis, url, job_ids, "Reopen")
            url = "{base}/jobs/manage?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
        except:
            self._handle_error(sys.exc_info())

    def create(
        self,
        template,
        count=1,
        name=None,
        start=None,
        end=None,
        priority=None,
        description=None,
        owner=None,
        group=None,
        assigned=None,
        complete=None,
        notes=None,
        parent=None,
        location=None,
        extended_properties=None,
        related_properties=None,
        job_id=None,
    ):
        """
        Adds a job to the Workflow Manager instance given a user-defined template

        ===================         ====================================================================
        **Argument**                **Description**
        -------------------         --------------------------------------------------------------------
        template                    Required object. Workflow Manager Job Template ID
        -------------------         --------------------------------------------------------------------
        count                       Optional Integer Number of jobs to create
        -------------------         --------------------------------------------------------------------
        name                        Optional string. Job Name
        -------------------         --------------------------------------------------------------------
        start                       Optional string. Job Start Date
        -------------------         --------------------------------------------------------------------
        end                         Optional string. Job End Date
        -------------------         --------------------------------------------------------------------
        priority                    Optional string. Job Priority Level
        -------------------         --------------------------------------------------------------------
        description                 Optional string. Job Description
        -------------------         --------------------------------------------------------------------
        owner                       Optional string. Job Owner
        -------------------         --------------------------------------------------------------------
        group                       Optional string Job Group
        -------------------         --------------------------------------------------------------------
        assigned                    Optional string. Initial Job Assignee
        -------------------         --------------------------------------------------------------------
        complete                    Optional Integer Percentage Complete
        -------------------         --------------------------------------------------------------------
        notes                       Optional string. Job Notes
        -------------------         --------------------------------------------------------------------
        parent                      Optional string Parent Job
        -------------------         --------------------------------------------------------------------
        location                    Optional Geometry. Define an area of location for your job.
        -------------------         --------------------------------------------------------------------
        extended_properties         Optional Dict. Define additional properties on a job template
                                    specific to your business needs.
        -------------------         --------------------------------------------------------------------
        related_properties          Optional Dict. Define additional 1-M properties on a job template
                                    specific to your business needs.
        -------------------         --------------------------------------------------------------------
        job_id                      Optional string. Define the unique jobId of the job to be created.
                                    Once defined, only one job can be created.
        ===================         ====================================================================

        :return:
            Workflow Manager :class:`~arcgis.gis.workflowmanager.Job`

        """
        job_object = {
            "numberOfJobs": count,
            "jobName": name,
            "startDate": start,
            "dueDate": end,
            "priority": priority,
            "description": description,
            "ownedBy": owner,
            "assignedType": group,
            "assignedTo": assigned,
            "percentComplete": complete,
            "notes": notes,
            "parentJob": parent,
            "location": location,
            "extendedProperties": extended_properties,
            "relatedProperties": related_properties,
            "jobId": job_id,
        }
        filtered_object = {}
        for key in job_object:
            if job_object[key] is not None:
                filtered_object[key] = job_object[key]
        url = "{base}/jobTemplates/{template}/job?token={token}".format(
            base=self._url, template=template, token=self._gis._con.token
        )
        return_obj = json.loads(
            self._gis._con.post(
                url,
                filtered_object,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj["jobIds"]

    def delete_attachment(self, job_id, attachment_id):
        """
        Deletes a job attachment given a job ID and attachment ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_id              Required string. Job ID
        ---------------     --------------------------------------------------------------------
        attachment_id       Required string. Attachment ID
        ===============     ====================================================================

        :return:
            status code

        """
        try:
            res = Job.delete_attachment(
                self._gis,
                "{base}/jobs/{jobId}/attachments/{attachmentId}?token={token}".format(
                    base=self._url,
                    jobId=job_id,
                    attachmentId=attachment_id,
                    item=self._item.id,
                    token=self._gis._con.token,
                ),
            )
            return res
        except:
            self._handle_error(sys.exc_info())

    def diagram(self, id):
        """
        Returns the job diagram for the user-defined job

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Job ID
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`Job Diagram <arcgis.gis.workflowmanager.JobDiagram>` object

        """
        try:
            return JobDiagram.get(
                self._gis,
                "{base}/jobs/{job}/diagram".format(base=self._url, job=id),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def get(self, id, get_ext_props=True):
        """
        Returns an active job with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Job ID
        ---------------     --------------------------------------------------------------------
        get_ext_props       Optional Boolean. If set to true will show the jobs extended properties.
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`Job <arcgis.gis.workflowmanager.Job>` Object

        """
        try:
            url = f"{self._url}/jobs/{id}"
            job_dict = self._gis._con.get(
                url, {"token": self._gis._con.token, "extProps": get_ext_props}
            )
            return Job(job_dict, self._gis, self._url)
        except:
            self._handle_error(sys.exc_info())

    def search(
        self,
        query=None,
        search_string=None,
        fields=None,
        display_names=[],
        sort_by=[],
        num=10,
        start_num=0,
    ):
        """
        Runs a search against the jobs stored inside the Workflow Manager instance

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        query               Required string. SQL query to search against (e.g. "priority='High'")
        ---------------     --------------------------------------------------------------------
        search_str          Optional string. Search string to search against (e.g. "High")
        ---------------     --------------------------------------------------------------------
        fields              Optional string. Field list to return
        ---------------     --------------------------------------------------------------------
        display_names       Optional string. Display names for the return fields
        ---------------     --------------------------------------------------------------------
        sort_by             Optional string. Field to sort by (e.g. {'field': 'priority', 'sortOrder': 'Asc'})
        ---------------     --------------------------------------------------------------------
        num                 Optional Integer. Number of return results
        ---------------     --------------------------------------------------------------------
        start_num           Optional string. Index of first return value
        ===============     ====================================================================

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_ of search results

        """
        try:
            search_object = {
                "q": query,
                "search": search_string,
                "num": num,
                "displayNames": display_names,
                "start": start_num,
                "sortFields": sort_by,
                "fields": fields,
            }
            url = "{base}/jobs/search?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
            return Job.search(self._gis, url, search_object)
        except:
            self._handle_error(sys.exc_info())

    def update(self, job_id, update_object):
        """
        Updates a job object by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_id              Required string. ID for the job to update
        ---------------     --------------------------------------------------------------------
        update_object       Required object. An object containing the fields and new values to add to the job
        ===============     ====================================================================

        :return:
            success object


        .. code-block:: python

            # USAGE EXAMPLE: Updating a Job's properties

            # create a WorkflowManager object from the workflow item
            >>> workflow_manager = WorkflowManager(wf_item)

            >>> job = workflow_manager.jobs.get(job_id)
            >>> job.priority = 'Updated'

            >>> table_name = job.extended_properties[0]["tableName"]
            >>> job.extended_properties = [
                    {
                        "identifier": table_name + ".prop1",
                        "value": "updated_123"
                    },
                    {
                        "identifier": table_name + ".prop2",
                        "value": "updated_456"
                    },
                ]

        >>> workflow_manager.jobs.update(job_id, vars(job))

        """
        try:
            current_job = self.get(job_id).__dict__
            for k in update_object.keys():
                current_job[k] = update_object[k]
            url = "{base}/jobs/{jobId}/update?token={token}".format(
                base=self._url, jobId=job_id, token=self._gis._con.token
            )
            new_job = Job(current_job, self._gis, url)
            # remove existing properties if not updating.
            if "extended_properties" not in update_object:
                new_job.extended_properties = None
            if "related_properties" not in update_object:
                new_job.related_properties = None

            # temporary fix for error in privileges
            delattr(new_job, "percent_complete")
            delattr(new_job, "parent_job")
            return new_job.post()
        except:
            self._handle_error(sys.exc_info())

    def upgrade(self, job_ids):
        """
        Upgrades a single or multiple jobs with specific JobIDs

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_ids             Required list. A list of job ID strings
        ===============     ====================================================================

        :return:
          success object

        """
        try:
            url = "{base}/jobs/manage?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
            return Job.manage_jobs(self._gis, url, job_ids, "Upgrade")
        except:
            self._handle_error(sys.exc_info())

    def set_job_location(self, job_id, geometry):
        """
        Set a location of work for an existing job. jobUpdateLocation privilege is required to set a location on a job.

        ===============     ====================================================================
        **Arguments**        **Description**
        ---------------     --------------------------------------------------------------------
        job_id              Required string. ID for the job to update
        ---------------     --------------------------------------------------------------------
        geometry            Required ArcGIS.Geometry.Geometry that describes a Job's Location.
                            Must be a Polygon, Polyline, or Multipoint geometry type
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/jobs/{jobId}/location?token={token}".format(
                base=self._url,
                jobId=job_id,
                item=self._item,
                token=self._gis._con.token,
            )
            location = {"geometryType": geometry.type}
            if geometry.type == "Polygon":
                location["geometry"] = json.dumps(
                    {
                        "rings": geometry.rings,
                        "spatialReference": geometry.spatial_reference,
                    }
                )
            elif geometry.type == "Polyline":
                location["geometry"] = json.dumps(
                    {
                        "paths": geometry.paths,
                        "spatialReference": geometry.spatial_reference,
                    }
                )
            elif geometry.type == "Multipoint":
                location["geometry"] = json.dumps(
                    {
                        "points": geometry.points,
                        "spatialReference": geometry.spatial_reference,
                    }
                )

            return_obj = json.loads(
                self._gis._con.put(
                    url,
                    {"location": location},
                    add_token=False,
                    post_json=True,
                    try_json=False,
                    json_encode=False,
                )
            )
            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]
            return_obj = {
                _camelCase_to_underscore(k): v
                for k, v in return_obj.items()
                if v is not None and not k.startswith("_")
            }
            return return_obj
        except:
            self._handle_error(sys.exc_info())

    def delete(self, job_ids):
        """
        Deletes a single or multiple jobs with specific JobIDs

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        job_ids             Required list. A list of job ID strings
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/jobs/manage?token={token}".format(
                base=self._url, token=self._gis._con.token
            )
            return Job.manage_jobs(self._gis, url, job_ids, "Delete")
        except:
            self._handle_error(sys.exc_info())


class WorkflowManager:
    """
    Represents a connection to a Workflow Manager instance or item.

    Users create, update, delete workflow diagrams, job templates and jobs
    or the various other properties with a workflow item.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    item                Required string. The Workflow Manager Item
    ===============     ====================================================================

    .. code-block:: python

        # USAGE EXAMPLE: Creating a WorkflowManager object from a workflow item

        from arcgis.workflow import WorkflowManager
        from arcgis.gis import GIS

        # connect to your GIS and get the web map item
        gis = GIS(url, username, password)
        wf_item = gis.content.get('1234abcd_workflow item id')

        # create a WorkflowManager object from the workflow item
        wm = WorkflowManager(wf_item)
        type(wm)
        >> arcgis.workflowmanager.WorkflowManager

        # explore the users in this workflow using the 'users' property
        wm.users
        >> [{}...{}]  # returns a list of dictionaries representing each user
    """

    def __init__(self, item):
        """initializer"""
        if item is None:
            raise ValueError("Item cannot be None")
        self._item = item
        self._gis = item._gis
        if self._gis.users.me is None:
            raise ValueError("An authenticated `GIS` is required.")

        self.job_manager = JobManager(item)
        self.saved_searches_manager = SavedSearchesManager(item)

        self._url = self._wmx_server_url[0]
        if self._url is None:
            raise ValueError("No WorkflowManager Registered with your Organization")
        if not any(
            prov.itemid == "50a5f00bcc574358b15eab0e2bdadf39"
            for prov in self._gis.users.me.provisions
        ):
            raise ValueError(
                "No Workflow Manager license is available for the current user"
            )

    def _handle_error(self, info):
        """Basic error handler - separated into a function to allow for expansion in future releases"""
        error_class = info[0]
        error_text = info[1]
        raise Exception(error_text)

    @property
    def _wmx_server_url(self):
        """locates the WMX server"""
        baseurl = self._gis._portal.resturl
        res = self._gis._con.get(f"{baseurl}/portals/self/servers", {"f": "json"})
        for s in res["servers"]:
            server_functions = [
                x.strip() for x in s.get("serverFunction", "").lower().split(",")
            ]
            if "workflowmanager" in server_functions:
                self._url = s.get("url", None)
                self._private_url = s.get("adminUrl", None)
                if self._url is None:
                    raise RuntimeError("Cannot find a WorkflowManager Server")
                self._url += f"/workflow/{self._item.id}"
                self._private_url += f"/workflow/{self._item.id}"
                return self._url, self._private_url
        raise RuntimeError(
            "Unable to locate Workflow Manager Server. Please contact your ArcGIS Enterprise "
            "Administrator to ensure Workflow Manager Server is properly configured."
        )
        return None

    @property
    def jobs(self):
        """
        The job manager for a workflow item.

        :return:
            :class:`~arcgis.gis.workflowmanager.JobManager` object

        """

        return self.job_manager

    def evaluate_arcade(
        self, expression, context=None, context_type="BaseContext", mode="Standard"
    ):
        """
        Evaluates an arcade expression

        ======================  ===============================================================
        **Argument**            **Description**
        ----------------------  ---------------------------------------------------------------
        expression              Required String.
        ----------------------  ---------------------------------------------------------------
        context                 Optional String.
        ----------------------  ---------------------------------------------------------------
        context_type            Optional String.
        ----------------------  ---------------------------------------------------------------
        mode                    Optional String.
        ======================  ===============================================================

        :return: String
        """
        url = f"{self._url}/evaluateArcade?token={self._gis._con.token}"
        params = {
            "expression": expression,
            "contextType": context_type,
            "context": context,
            "parseMode": mode,
        }
        res = self._gis._con.post(url, params=params, json_encode=False, post_json=True)
        return res.get("result", None)

    @property
    def wm_roles(self):
        """
        Returns a list of user :class:`roles <arcgis.gis.workflowmanager.WMRole>` available
        in the local Workflow Manager instance.

        :return: list
        """
        try:
            role_array = self._gis._con.get(
                "{base}/community/roles".format(base=self._url),
                params={"token": self._gis._con.token},
            )["roles"]
            return_array = [WMRole(r) for r in role_array]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    @property
    def users(self):
        """
        Returns an list of all user profiles stored in Workflow Manager

        :return: List of :attr:`~arcgis.gis.workflowmanager.WorkflowManager.user` profiles
        """
        try:
            user_array = self._gis._con.get(
                "{base}/community/users".format(base=self._url),
                params={"token": self._gis._con.token},
            )["users"]
            return_array = [self.user(u["username"]) for u in user_array]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    @property
    def assignable_users(self):
        """
        Get all assignable users for a user in the workflow system

        :return:
            A `list <https://docs.python.org/3/library/stdtypes.html#list>`_ of the assignable :attr:`~assarcgis.gis.workflowmanager.WorkflowManager.user` objects

        """
        try:
            user_array = self._gis._con.get(
                "{base}/community/users".format(base=self._url),
                params={"token": self._gis._con.token},
            )["users"]
            return_array = [
                self.user(u["username"]) for u in user_array if u["isAssignable"]
            ]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    @property
    def assignable_groups(self):
        """
        Get portal groups associated with Workflow Manager roles, to which the current user
        can assign work based on their Workflow Manager assignment privileges.

        :return:
            A `list <https://docs.python.org/3/library/stdtypes.html#list>`_ of
            the assignable :class:`~arcgis.gis.workflowmanager.Group` objects

        """
        try:
            group_array = self._gis._con.get(
                "{base}/community/groups".format(base=self._url),
                params={"token": self._gis._con.token},
            )["groups"]
            return_array = [
                self.group(g["id"]) for g in group_array if g["isAssignable"]
            ]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    @property
    def settings(self):
        """
        Returns a list of all settings for the Workflow Manager instance

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_

        """
        try:
            return self._gis._con.get(
                "{base}/settings".format(base=self._url),
                params={"token": self._gis._con.token},
            )["settings"]
        except:
            self._handle_error(sys.exc_info())

    @property
    def groups(self):
        """
        Returns an list of all user :class:`groups <arcgis.gis.workflowmanager.Group>`
        stored in Workflow Manager

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_

        """
        try:
            group_array = self._gis._con.get(
                "{base}/community/groups".format(base=self._url),
                params={"token": self._gis._con.token},
            )["groups"]
            return_array = [self.group(g["id"]) for g in group_array]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    def searches(self, search_type=None):
        """
        Returns a list of all saved searches.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        search_type         Optional string. The search type for returned saved searches.
                            The accepted values are `Standard`, `Chart`, and `All`. If not
                            defined, the Standard searches are returned.
        ===============     ====================================================================

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_

        """
        params = {"token": self._gis._con.token}
        if search_type is not None:
            params["searchType"] = search_type

        try:
            return self._gis._con.get(
                "{base}/searches".format(base=self._url), params=params
            )["searches"]
        except:
            self._handle_error(sys.exc_info())

    @property
    def job_templates(self):

        """
        Gets all the job templates in a workflow item.

        :return:
            List of all current :class:`job templates <arcgis.gis.workflowmanager.JobTemplate>`
            in the Workflow Manager (required information for create_job call).

        """
        try:
            template_array = self._gis._con.get(
                "{base}/jobTemplates".format(base=self._url),
                params={"token": self._gis._con.token},
            )["jobTemplates"]
            return_array = [
                JobTemplate(t, self._gis, self._url) for t in template_array
            ]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    @property
    def diagrams(self):
        """
        Gets the workflow diagrams within the workflow item.

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_ of all current
            :class:`diagrams <arcgis.gis.workflowmanager.JobDiagram>` in the Workflow Manager

        """
        try:
            diagram_array = self._gis._con.get(
                "{base}/diagrams".format(base=self._url),
                params={"token": self._gis._con.token},
            )["diagrams"]
            return_array = [JobDiagram(d, self._gis, self._url) for d in diagram_array]
            return return_array
        except:
            self._handle_error(sys.exc_info())

    def update_settings(self, props):
        """
        Returns an active job with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        props               Required list. A list of Props objects to update
                            (Prop object example: {'propName': 'string', 'value': 'string'})
        ===============     ====================================================================

        :return:
            success object

        """
        url = "{base}/settings?token={token}".format(
            base=self._url, token=self._gis._con.token
        )
        params = {"settings": props}
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    def wm_role(self, name):
        """
        Returns an active role with the given name

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        name                Required string. Role Name
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`Role <arcgis.gis.workflowmanager.WMRole>` Object

        """
        try:
            return WMRole.get(
                self._gis,
                "{base}/community/roles/{role}".format(
                    base=self._url, role=urllib.parse.quote(name), item=self._item.id
                ),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def job_template(self, id):
        """
        Returns a job template with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Job Template ID
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`JobTemplate <arcgis.gis.workflowmanager.JobTemplate>` Object

        """
        try:
            return JobTemplate.get(
                self._gis,
                "{base}/jobTemplates/{jobTemplate}".format(
                    base=self._url, jobTemplate=id
                ),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def delete_job_template(self, id):
        """
        Deletes a job template with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Job Template ID
        ===============     ====================================================================

        :return:
            status code

        """
        try:
            res = JobTemplate.delete(
                self._gis,
                "{base}/jobTemplates/{jobTemplate}?token={token}".format(
                    base=self._url,
                    jobTemplate=id,
                    item=self._item.id,
                    token=self._gis._con.token,
                ),
            )
            return res
        except:
            self._handle_error(sys.exc_info())

    def user(self, username):
        """
        Returns a user profile with the given username

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        username            Required string. Workflow Manager Username
        ===============     ====================================================================

        :return:
            Workflow Manager user profile

        """
        try:
            return arcgis.gis.User(self._gis, username)
        except:
            self._handle_error(sys.exc_info())

    def group(self, group_id):
        """
        Returns group information with the given group ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        group_id            Required string. Workflow Manager Group ID
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`~arcgis.gis.workflowmanager.Group` Object

        """
        try:
            wmx_group = Group.get(
                self._gis,
                "{base}/community/groups/{groupid}".format(
                    base=self._url, groupid=group_id, item=self._item.id
                ),
                {"token": self._gis._con.token},
            )
            arcgis_group = arcgis.gis.Group(self._gis, group_id)
            arcgis_group.roles = wmx_group.roles
            return arcgis_group
        except:
            self._handle_error(sys.exc_info())

    def update_group(self, group_id, update_object):
        """
        Update the information to the portal group. The adminAdvanced privilege is required.
        New roles can be added to the portal group. Existing roles can be deleted from the portal group.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        group_id            Required string. :class:`Workflow Manager Group <arcgis.gis.workflowmanager.Group>` ID
        ---------------     --------------------------------------------------------------------
        update_object       Required object. Object containing the updated actions of the information to be taken to the portal group.
        ===============     ====================================================================

        :return:
            boolean

        """
        url = "{base}/community/groups/{groupid}?token={token}".format(
            base=self._url, groupid=group_id, token=self._gis._con.token
        )

        return_obj = json.loads(
            self._gis._con.post(
                url,
                update_object,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )

        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]

        return return_obj

    def diagram(self, id):
        """
        Returns the :class:`diagram <arcgis.gis.workflowmanager.JobDiagram>` with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Diagram ID
        ===============     ====================================================================

        :return:
             Workflow Manager :class:`~arcgis.gis.workflowmanager.JobDiagram` Object

        """
        try:
            return JobDiagram.get(
                self._gis,
                "{base}/diagrams/{diagram}".format(base=self._url, diagram=id),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def diagram_version(self, diagram_id, version_id):
        """
        Returns the :class:`diagram <arcgis.gis.workflowmanager.JobDiagram>` with the given version ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        diagram_id          Required string. Diagram ID
        ---------------     --------------------------------------------------------------------
        version_id          Required string. Diagram Version ID
        ===============     ====================================================================

        :return:
             Specified version of the Workflow Manager :class:`~arcgis.gis.workflowmanager.JobDiagram` object

        """
        try:
            return JobDiagram.get(
                self._gis,
                "{base}/diagrams/{diagram}/{diagramVersion}".format(
                    base=self._url, diagram=diagram_id, diagramVersion=version_id
                ),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def create_wm_role(self, name, description="", privileges=[]):
        """
        Adds a role to the Workflow Manager instance given a user-defined name

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        name                Required string. Role Name (required)
        ---------------     --------------------------------------------------------------------
        description         Required string. Role Description
        ---------------     --------------------------------------------------------------------
        privileges          Required list. List of privileges associated with the role
        ===============     ====================================================================

        :return:
            Workflow Manager :class:`Role <arcgis.gis.workflowmanager.WMRole>` Object

        """
        try:
            url = "{base}/community/roles/{name}?token={token}".format(
                base=self._url, name=name, token=self._gis._con.token
            )
            post_role = WMRole(
                {"roleName": name, "description": description, "privileges": privileges}
            )
            return post_role.post(self._gis, url)
        except:
            self._handle_error(sys.exc_info())

    def create_job_template(
        self,
        name,
        priority,
        id=None,
        category="",
        job_duration=0,
        assigned_to="",
        default_due_date=None,
        default_start_date=None,
        start_date_type="CreationDate",
        diagram_id="",
        diagram_name="",
        assigned_type="Unassigned",
        description="",
        default_description="",
        state="Draft",
        last_updated_by="",
        last_updated_date=None,
        extended_property_table_definitions=[],
    ):
        """
        Adds a job template to the Workflow Manager instance given a user-defined name and default priority level

        ====================================     ====================================================================
        **Argument**                             **Description**
        ------------------------------------     --------------------------------------------------------------------
        name                                     Required string. Job Template Name
        ------------------------------------     --------------------------------------------------------------------
        priority                                 Required string. Default Job Template Priority Level
        ------------------------------------     --------------------------------------------------------------------
        id                                       Optional string. Job Template ID
        ------------------------------------     --------------------------------------------------------------------
        category                                 Optional string. Job Template Category
        ------------------------------------     --------------------------------------------------------------------
        job_duration                             Optional string. Default Job Template Duration
        ------------------------------------     --------------------------------------------------------------------
        assigned_to                              Optional string. Job Owner
        ------------------------------------     --------------------------------------------------------------------
        default_due_date                         Optional string. Due Date for Job Template
        ------------------------------------     --------------------------------------------------------------------
        default_start_date                       Optional string. Start Date for Job Template
        ------------------------------------     --------------------------------------------------------------------
        start_date_type                          Optional string. Type of Start Date (e.g. creationDate)
        ------------------------------------     --------------------------------------------------------------------
        diagram_id                               Optional string. Job Template Diagram ID
        ------------------------------------     --------------------------------------------------------------------
        diagram_name                             Optional string. Job Template Diagram Name
        ------------------------------------     --------------------------------------------------------------------
        assigned_type                            Optional string. Type of Job Template Assignment
        ------------------------------------     --------------------------------------------------------------------
        description                              Optional string. Job Template Description
        ------------------------------------     --------------------------------------------------------------------
        default_description                      Optional string. Default Job Template Description
        ------------------------------------     --------------------------------------------------------------------
        state                                    Optional string. Default Job Template State
        ------------------------------------     --------------------------------------------------------------------
        last_updated_by                          Optional string. User Who Last Updated Job Template
        ------------------------------------     --------------------------------------------------------------------
        last_updated_date                        Optional string. Date of Last Job Template Update
        ------------------------------------     --------------------------------------------------------------------
        extended_property_table_definitions      Optional list. List of Extended Properties for Job Template
        ====================================     ====================================================================

        :return:
            Workflow Manager :class:`~arcgis.gis.workflowmanager.JobTemplate` ID

        """
        try:
            if default_due_date is None:
                default_due_date = datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            if default_start_date is None:
                default_start_date = datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            if last_updated_date is None:
                last_updated_date = datetime.datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            url = "{base}/jobTemplates?token={token}".format(
                base=self._url, token=self._gis._con.token
            )

            post_job_template = JobTemplate(
                {
                    "jobTemplateId": id,
                    "jobTemplateName": name,
                    "category": category,
                    "defaultJobDuration": job_duration,
                    "defaultAssignedTo": assigned_to,
                    "defaultDueDate": default_due_date,
                    "defaultStartDate": default_start_date,
                    "jobStartDateType": start_date_type,
                    "diagramId": diagram_id,
                    "diagramName": diagram_name,
                    "defaultPriorityName": priority,
                    "defaultAssignedType": assigned_type,
                    "description": description,
                    "defaultDescription": default_description,
                    "state": state,
                    "extendedPropertyTableDefinitions": extended_property_table_definitions,
                    "lastUpdatedBy": last_updated_by,
                    "lastUpdatedDate": last_updated_date,
                }
            )

            return post_job_template.post(self._gis, url)
        except:
            self._handle_error(sys.exc_info())

    def update_job_template(self, template):
        """
        Updates a job template object by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        body                Required object. :class:`Job Template <arcgis.gis.workflowmanger.JobTemplate>`
                            body. Existing Job Template object that inherits required/optional fields.
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/jobTemplates/{jobTemplate}?token={token}".format(
                base=self._url,
                jobTemplate=template["job_template_id"],
                item=self._item.id,
                token=self._gis._con.token,
            )
            template_object = JobTemplate(template)
            res = template_object.put(self._gis, url)
            return res
        except:
            self._handle_error(sys.exc_info())

    def create_diagram(
        self,
        name,
        steps,
        display_grid,
        description="",
        active=False,
        annotations=[],
        data_sources=[],
        diagram_id=None,
    ):
        """
        Adds a diagram to the Workflow Manager instance given a user-defined name and array of steps

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        name                Required string. Diagram Name
        ---------------     --------------------------------------------------------------------
        steps               Required list. List of Step objects associated with the Diagram
        ---------------     --------------------------------------------------------------------
        display_grid        Required boolean. Boolean indicating whether the grid will be displayed in the Diagram
        ---------------     --------------------------------------------------------------------
        description         Optional string. Diagram description
        ---------------     --------------------------------------------------------------------
        active              Optional Boolean. Indicates whether the Diagram is active
        ---------------     --------------------------------------------------------------------
        annotations         Optinal list. List of Annotation objects associated with the Diagram
        ---------------     --------------------------------------------------------------------
        data_sources        Optional list. List of Data Source objects associated with the Diagram
        ---------------     --------------------------------------------------------------------
        diagram_id          Optional string. The unique ID of the diagram to be created.
        ===============     ====================================================================

        :return:
            :class:`Workflow Manager Diagram <arcgis.gis.workflowmanager.JobDiagram>` ID

        """
        try:
            url = "{base}/diagrams?token={token}".format(
                base=self._url, token=self._gis._con.token
            )

            post_diagram = JobDiagram(
                {
                    "diagramId": diagram_id,
                    "diagramName": name,
                    "description": description,
                    "active": active,
                    "initialStepId": "",
                    "initialStepName": "",
                    "steps": steps,
                    "dataSources": data_sources,
                    "annotations": annotations,
                    "displayGrid": display_grid,
                }
            )
            return post_diagram.post(self._gis, url)["diagram_id"]
        except:
            self._handle_error(sys.exc_info())

    def update_diagram(self, body, delete_draft=True):
        """
        Updates a diagram object by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        body                Required object. Diagram body - existing Diagram object that inherits required/optional
                            fields.
        ---------------     --------------------------------------------------------------------
        delete_draft        Optional Boolean - option to delete the Diagram draft (optional)
        ===============     ====================================================================

        :return:
            success object

        """
        try:
            url = "{base}/diagrams/{diagramid}?token={token}".format(
                base=self._url, diagramid=body["diagram_id"], token=self._gis._con.token
            )
            post_diagram = JobDiagram(
                {
                    "diagramId": body["diagram_id"],
                    "diagramName": body["diagram_name"],
                    "description": (
                        body["description"] if "description" in body else ""
                    ),
                    "active": (body["active"] if "active" in body else False),
                    "initialStepId": (
                        body["initial_step_id"] if "initial_step_id" in body else ""
                    ),
                    "initialStepName": (
                        body["initial_step_name"] if "initial_step_name" in body else ""
                    ),
                    "steps": body["steps"],
                    "dataSources": (
                        body["data_sources"] if "data_sources" in body else []
                    ),
                    "annotations": (
                        body["annotations"] if "annotations" in body else ""
                    ),
                    "displayGrid": body["display_grid"],
                }
            )
            res = post_diagram.update(self._gis, url, delete_draft)

            return res
        except:
            self._handle_error(sys.exc_info())

    def delete_diagram(self, id):
        """
        Deletes a diagram object by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Diagram id
        ===============     ====================================================================

        :return:
            :class:`Workflow Manager Diagram <arcgis.gis.workflowmanager.JobDiagram>` ID

        """
        try:
            url = "{base}/diagrams/{diagramid}?token={token}".format(
                base=self._url, diagramid=id, token=self._gis._con.token
            )
            return JobDiagram.delete(self._gis, url)
        except:
            self._handle_error(sys.exc_info())

    def delete_diagram_version(self, diagram_id, version_id):
        """
        Deletes a diagram version by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        diagram_id          Required string. Diagram ID
        ---------------     --------------------------------------------------------------------
        version_id          Required string. Diagram Version ID
        ===============     ====================================================================

        :return:
            boolean

        """
        try:
            url = "{base}/diagrams/{diagramid}/{diagramVersion}?token={token}".format(
                base=self._url,
                diagramid=diagram_id,
                diagramVersion=version_id,
                token=self._gis._con.token,
            )
            return JobDiagram.delete(self._gis, url)
        except:
            self._handle_error(sys.exc_info())

    @property
    def saved_searches(self):
        """
        The Saved Searches manager for a workflow item.

        :return:
            :class:`~arcgis.gis.workflowmanager.SavedSearchesManager`

        """

        return self.saved_searches_manager

    @property
    def table_definitions(self):
        """
        Get the definitions of each extended properties table in a workflow item. The response will consist of a list
        of table definitions. If the extended properties table is a feature service, its definition will include a
        dictionary of feature service properties. Each table definition will also include definitions of the properties
        it contains and list the associated job templates. This requires the adminBasic or adminAdvanced privileges.

        :return:
            `list <https://docs.python.org/3/library/stdtypes.html#list>`_

        """

        url = "{base}/tableDefinitions?token={token}".format(
            base=self._url, token=self._gis._con.token
        )

        return_obj = self._gis._con.get(url)
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]

        return return_obj["tableDefinitions"]

    def lookups(self, lookup_type):
        """
        Returns LookUp Tables by given type

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        lookup_type         Required string. The type of lookup table stored in the workflow item.
        ===============     ====================================================================

        :return:
           Workflow Manager :class:`LookUpTable <arcgis.gis.workflowmanager.LookUpTable>` Object

        """
        try:
            return LookUpTable.get(
                self._gis,
                "{base}/lookups/{lookupType}".format(
                    base=self._url, lookupType=lookup_type
                ),
                {"token": self._gis._con.token},
            )
        except:
            self._handle_error(sys.exc_info())

    def delete_lookup(self, lookup_type):
        """
        Deletes a job template with the given ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        lookup_type         Required string. The type of lookup table stored in the workflow item.
        ===============     ====================================================================

        :return:
            status code

        """
        try:
            res = LookUpTable.delete(
                self._gis,
                "{base}/lookups/{lookupType}?token={token}".format(
                    base=self._url,
                    lookupType=lookup_type,
                    item=self._item.id,
                    token=self._gis._con.token,
                ),
            )
            return res
        except:
            self._handle_error(sys.exc_info())

    def create_lookup(self, lookup_type, lookups):
        """
        Adds a diagram to the Workflow Manager instance given a user-defined name and array of steps

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        lookup_type         Required string. The type of lookup table stored in the workflow item.
        ---------------     --------------------------------------------------------------------
        lookups             Required list. List of lookups to be created / updated
        ===============     ====================================================================

        :return:
            boolean

        .. code-block:: python

            # USAGE EXAMPLE: Creating a Lookup Table

            # create a WorkflowManager object from the workflow item
            wm = WorkflowManager(wf_item)

            # create the lookups object
            lookups = [{"lookupName": "Low", "value": 0},
                       {"lookupName": "Medium", "value": 5},
                       {"lookupName": "High", "value": 10},
                       {"lookupName": "EXTRA", "value": 15},
                       {"lookupName": "TEST", "value": 110}]

            wm.create_lookup("priority", lookups)
            >> True  # returns true if created successfully
        """
        try:
            url = "{base}/lookups/{lookupType}?token={token}".format(
                base=self._url, lookupType=lookup_type, token=self._gis._con.token
            )

            post_lookup = LookUpTable({"lookups": lookups})

            return post_lookup.put(self._gis, url)
        except:
            self._handle_error(sys.exc_info())


class LookUpTable(object):
    """
    Represents a Workflow Manager Look Up object with accompanying GET, POST, and DELETE methods.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    init_data           data object containing the relevant properties for a LookUpTable to complete REST calls
    ===============     ====================================================================
    """

    _camelCase_to_underscore = _camelCase_to_underscore
    _underscore_to_camelcase = _underscore_to_camelcase

    def __init__(self, init_data, gis=None, url=None):
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])
        self._gis = gis
        self._url = url

    def __getattr__(self, item):
        gis = object.__getattribute__(self, "_gis")
        url = object.__getattribute__(self, "_url")
        id = object.__getattribute__(self, "job_template_id")
        full_object = gis._con.get(url, {"token": gis._con.token})
        try:
            setattr(self, _camelCase_to_underscore(item), full_object[item])
            return full_object[item]
        except KeyError:
            raise KeyError(f'The attribute "{item}" is invalid for LookUpTables')

    def get(gis, url, params):
        lookup_dict = gis._con.get(url, params)
        return LookUpTable(lookup_dict, gis, url)

    def put(self, gis, url):
        put_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        return_obj = json.loads(
            gis._con.put(
                url,
                put_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def delete(gis, url):
        return_obj = json.loads(gis._con.delete(url, add_token=False, try_json=False))
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj


class SavedSearchesManager:
    """
    Represents a helper class for workflow manager saved searches. Accessible as the
    :attr:`~arcgis.gis.workflowmanager.WorkflowManager.saved_searches` property.

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    item                The Workflow Manager Item
    ===============     ====================================================================

    """

    def __init__(self, item):
        """initializer"""
        if item is None:
            raise ValueError("Item cannot be None")
        self._item = item
        self._gis = item._gis
        if self._gis.users.me is None:
            raise ValueError("An authenticated `GIS` is required.")

        self._url = self._wmx_server_url[0]
        if self._url is None:
            raise ValueError("No WorkflowManager Registered with your Organization")
        if not any(
            prov.itemid == "50a5f00bcc574358b15eab0e2bdadf39"
            for prov in self._gis.users.me.provisions
        ):
            raise ValueError(
                "No Workflow Manager license is available for the current user"
            )

    def _handle_error(self, info):
        """Basic error handler - separated into a function to allow for expansion in future releases"""
        error_class = info[0]
        error_text = info[1]
        raise Exception(error_text)

    @property
    def _wmx_server_url(self):
        """locates the WMX server"""
        baseurl = self._gis._portal.resturl
        res = self._gis._con.get(f"{baseurl}/portals/self/servers", {"f": "json"})
        for s in res["servers"]:
            server_functions = [
                x.strip() for x in s.get("serverFunction", "").lower().split(",")
            ]
            if "workflowmanager" in server_functions:
                self._url = s.get("url", None)
                self._private_url = s.get("adminUrl", None)
                if self._url is None:
                    raise RuntimeError("Cannot find a WorkflowManager Server")
                self._url += f"/workflow/{self._item.id}"
                self._private_url += f"/workflow/{self._item.id}"
                return self._url, self._private_url
        raise RuntimeError(
            "Unable to locate Workflow Manager Server. Please contact your ArcGIS Enterprise "
            "Administrator to ensure Workflow Manager Server is properly configured."
        )
        return None

    def create(
        self,
        name,
        search_type,
        folder=None,
        definition=None,
        color_ramp=None,
        sort_index=None,
        search_id=None,
    ):
        """
        Create a saved search or chart by specifying the search parameters in the json body.
        All search properties except for optional properties must be passed in the body to save the search or chart.
        The adminAdvanced or adminBasic privilege is required.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        name                Required string. The display name for the saved search or chart.
        ---------------     --------------------------------------------------------------------
        search_type         Required string. The type for the saved search or chart. The accepted values are Standard, Chart and All.
        ---------------     --------------------------------------------------------------------
        folder              Optional string. The folder the saved search or chart will be categorized under.
        ---------------     --------------------------------------------------------------------
        definition          Required string. if the searchType is Standard. The search definition to be saved.
        ---------------     --------------------------------------------------------------------
        color_ramp          Required string. if the searchType is Chart. The color ramp for the saved chart.
        ---------------     --------------------------------------------------------------------
        sort_index          Optional string. The sorting order for the saved search or chart.
        ---------------     --------------------------------------------------------------------
        search_id           Optional string. The unique ID of the search or chart to be created.
        ===============     ====================================================================

        :return:
            Saved Search ID

        """
        try:
            url = "{base}/searches?token={token}".format(
                base=self._url, id=search_id, token=self._gis._con.token
            )
            post_dict = {
                "name": name,
                "folder": folder,
                "definition": definition,
                "searchType": search_type,
                "colorRamp": color_ramp,
                "sortIndex": sort_index,
                "searchId": search_id,
            }
            post_dict = {k: v for k, v in post_dict.items() if v is not None}
            return_obj = json.loads(
                self._gis._con.post(
                    url,
                    post_dict,
                    add_token=False,
                    post_json=True,
                    try_json=False,
                    json_encode=False,
                )
            )

            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]

            return return_obj["searchId"]
        except:
            self._handle_error(sys.exc_info())

    def delete(self, id):
        """
        Deletes a saved search by ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        id                  Required string. Saved Search id
        ===============     ====================================================================

        :return:
            boolean
        """
        try:
            url = "{base}/searches/{searchid}?token={token}".format(
                base=self._url, searchid=id, token=self._gis._con.token
            )

            return_obj = json.loads(
                self._gis._con.delete(url, add_token=False, try_json=False)
            )

            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]
        except:
            self._handle_error(sys.exc_info())

    def update(self, search):
        """
        Update a saved search or chart by specifying the update values in the json body.
        All the properties except for optional properties must be passed in the body
        to update the search or chart. The searchId cannot be updated once it is created.
        The adminAdvanced or adminBasic privilege is required.

        ===============     ====================================================================
        **Arguments**        **Description**
        ---------------     --------------------------------------------------------------------
        search              Required object. An object defining the properties of the search to be updated.
        ===============     ====================================================================

        :return: success object

        .. code-block:: python

            # USAGE EXAMPLE: Updating a Job's properties

            # create a WorkflowManager object from the workflow item
            >>> workflow_manager = WorkflowManager(wf_item)

            >>> workflow_manager.create_saved_search(name="name",
                                                    definition={
                                                        "start": 0,
                                                        "fields": ["job_status"],
                                                        "displayNames": ["Status"  ],
                                                        "sortFields": [{"field": "job_status",
                                                                        "sortOrder": "Asc:}]
                                                                },
                                                    search_type='Chart',
                                                    color_ramp='Flower Field Inverse',
                                                    sort_index=2000)

            >>> search_lst = workflow_manager.searches("All")
            >>> search = [x for x in search_lst if x["searchId"] == searchid][0]

            >>> search["colorRamp"] = "Default"
            >>> search["name"] = "Updated search"

            >>> actual = workflow_manager.update_saved_search(search)

        """
        try:
            url = "{base}/searches/{searchId}?token={token}".format(
                base=self._url, searchId=search["searchId"], token=self._gis._con.token
            )
            return_obj = json.loads(
                self._gis._con.put(
                    url,
                    search,
                    add_token=False,
                    post_json=True,
                    try_json=False,
                    json_encode=False,
                )
            )

            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]
            return return_obj
        except:
            self._handle_error(sys.exc_info())

    def share(self, search_id, group_ids):
        """
        Shares a saved search with the list of groups

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        search_id           Required string. Saved Search id
        ---------------     --------------------------------------------------------------------
        group_ids           Required list. List of Workflow Group Ids
        ===============     ====================================================================

        :return:
            boolean
        """
        try:
            url = "{base}/searches/{searchId}/shareWith?token={token}".format(
                base=self._url, searchId=search_id, token=self._gis._con.token
            )
            post_dict = {"groupIds": group_ids}

            return_obj = json.loads(
                self._gis._con.post(
                    url,
                    post_dict,
                    add_token=False,
                    post_json=True,
                    try_json=False,
                    json_encode=False,
                )
            )

            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]
        except:
            self._handle_error(sys.exc_info())

    def share_details(self, search_id):
        """
        Returns the list of groups that the saved search is shared with by searchId.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        search_id           Search ID
        ===============     ====================================================================

        :return:
            list of :class:`~arcgis.gis.workflowmanager.Group` ID

        """

        url = "{base}/searches/{searchId}/shareWith?token={token}".format(
            base=self._url, searchId=search_id, token=self._gis._con.token
        )

        return_obj = self._gis._con.get(url)

        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj["groupIds"]


class Job(object):
    """
    Helper class for managing Workflow Manager jobs in a workflow item. This class is
    not created by users directly. An instance of this class, can be created by calling
    the :meth:`get <arcgis.gis.workflowmanager.JobManager.get>` method of the
    ``Job Manager`` with the appropriate job ID. The
    :class:`~arcgis.gis.workflowmanager.JobManager` is accessible as the
    :attr:`~arcgis.gis.workflowmanager.WorkflowManager.jobs` property of the
    :class:`~arcgis.gis.workflowmanager.WorkflowManager`.

    """

    _camelCase_to_underscore = _camelCase_to_underscore
    _underscore_to_camelcase = _underscore_to_camelcase

    def __init__(self, init_data, gis=None, url=None):
        self.job_status = (
            self.notes
        ) = (
            self.diagram_id
        ) = (
            self.end_date
        ) = (
            self.due_date
        ) = (
            self.description
        ) = (
            self.started_date
        ) = (
            self.current_steps
        ) = (
            self.job_template_name
        ) = (
            self.job_template_id
        ) = (
            self.extended_properties
        ) = (
            self.diagram_name
        ) = (
            self.parent_job
        ) = (
            self.job_name
        ) = (
            self.diagram_version
        ) = (
            self.active_versions
        ) = (
            self.percent_complete
        ) = (
            self.priority
        ) = (
            self.job_id
        ) = (
            self.created_date
        ) = (
            self.created_by
        ) = (
            self.closed
        ) = (
            self.owned_by
        ) = self.start_date = self._location = self.related_properties = None
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])
        self._gis = gis
        self._url = url

    def post(self):
        post_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None and not k.startswith("_")
        }
        return_obj = json.loads(
            self._gis._con.post(
                self._url,
                post_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    def search(gis, url, search_object):
        return_obj = json.loads(
            gis._con.post(
                url,
                search_object,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def get_attachment(self, attachment_id):
        """
        Returns an embedded job attachment given an attachment ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        attachment_id       Attachment ID
        ===============     ====================================================================

        :return:
            Job Attachment

        """

        url = "{base}/jobs/{jobId}/attachments/{attachmentId}".format(
            base=self._url, jobId=self.job_id, attachmentId=attachment_id
        )
        return_obj = self._gis._con.get(
            url, {"token": self._gis._con.token}, try_json=False
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj

    def add_attachment(self, attachment, alias=None, folder=None):
        """
        Adds an attachment to the job

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        attachment          Filepath to attachment
        ---------------     --------------------------------------------------------------------
        alias               Optional string. Alias for the attachment
        ---------------     --------------------------------------------------------------------
        folder              Optional string. Folder for the attachment
        ===============     ====================================================================

        :return:
            Job Attachment

        """
        url = "{base}/jobs/{jobId}/attachments".format(
            base=self._url, jobId=self.job_id
        )
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params={"alias": alias, "folder": folder},
                files={"attachment": attachment},
                add_token=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        return {"id": return_obj["url"].split("/")[-1], "alias": return_obj["alias"]}

    def add_linked_attachment(self, attachments):
        """
        Add linked attachments to a job to provide additional or support information related to the job.
        Linked attachments can be links to a file on a local or shared file system or a URL.
        jobUpdateAttachments privilege is required to add an attachment to a job.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        attachments         List of linked attachments to associate with the job.
                            Each attachment should define the url, alias and folder
        ===============     ====================================================================

        :return:
            `List <https://docs.python.org/3/library/stdtypes.html#list>`_ list of job attachments

        """
        url = "{base}/jobs/{jobId}/attachmentslinked?token={token}".format(
            base=self._url, jobId=self.job_id, token=self._gis._con.token
        )

        post_object = {"attachments": attachments}
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params=post_object,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        return return_obj["attachments"]

    def update_attachment(self, attachment_id, alias):
        """
        Updates an attachment alias given a Job ID and attachment ID

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        attachment_id       Attachment ID
        ---------------     --------------------------------------------------------------------
        alias               Alias
        ===============     ====================================================================

        :return:
            success

        """
        url = "{base}/jobs/{jobId}/attachments/{attachmentid}".format(
            base=self._url, jobId=self.job_id, attachmentid=attachment_id
        )
        post_object = {"alias": alias}
        return_obj = json.loads(
            self._gis._con.post(
                url, params=post_object, try_json=False, json_encode=False
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def delete_attachment(gis, url):
        return_obj = json.loads(gis._con.delete(url, add_token=False, try_json=False))
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def update_step(self, step_id, assigned_type, assigned_to):
        """
        Update the assignment of the current step in a job based on the current user's Workflow Manager assignment privileges

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        step_id             Active Step ID
        ---------------     --------------------------------------------------------------------
        assigned_type       Type of assignment designated (NOTE: Must be User, Group or Unassigned)
        ---------------     --------------------------------------------------------------------
        assigned_to         User to which the active step is assigned
        ===============     ====================================================================

        :return:
            success object

        """

        if step_id is None:
            step_id = self.currentSteps[0]["step_id"]
        url = "{base}/jobs/{jobId}/{stepId}?token={token}".format(
            base=self._url,
            jobId=self.job_id,
            stepId=step_id,
            token=self._gis._con.token,
        )
        post_object = {"assignedType": assigned_type, "assignedTo": assigned_to}
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params=post_object,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def set_current_step(self, step_id):
        """
        Sets a single step to be the active step on the job. The ability to set a step as current is controlled by the **workflowSetStepCurrent** privilege.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        step_id             Active Step ID
        ===============     ====================================================================

        :return:
            success object

        """

        url = "{base}/jobs/{jobId}/action?token={token}".format(
            base=self._url, jobId=self.job_id, token=self._gis._con.token
        )
        post_object = {"type": "SetCurrentStep", "stepIds": [step_id]}
        return_obj = json.loads(
            self._gis._con.post(
                url,
                params=post_object,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    @property
    def attachments(self):
        """
        Gets the attachments of a job given job ID

        :return:
            `list <https://docs.python.org/3/library/stdtypes.html#list>`_ of attachments

        """

        url = "{base}/jobs/{jobId}/attachments?token={token}".format(
            base=self._url, jobId=self.job_id, token=self._gis._con.token
        )
        return_obj = self._gis._con.get(url)
        return return_obj["attachments"]

    @property
    def history(self):
        """
        Gets the history of a job given job ID

        :return:
            success object

        """

        url = "{base}/jobs/{jobId}/history?token={token}".format(
            base=self._url, jobId=self.job_id, token=self._gis._con.token
        )
        return_obj = self._gis._con.get(url)
        if "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    @property
    def location(self):
        """
        Get/Set the job location for the user-defined job

        :return:
            Workflow Manager :class:`~arcgis.gis.workflowmanager.JobLocation` object
        """

        if self._location is None:
            self._location = JobLocation.get(
                self._gis,
                "{base}/jobs/{job}/location".format(base=self._url, job=self.job_id),
                {"token": self._gis._con.token},
            )
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    def manage_jobs(gis, url, ids, action):
        post_object = {"jobIds": ids, "type": action}
        return_obj = json.loads(
            gis._con.post(
                url,
                params=post_object,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def add_comment(self, comment):
        """
        Adds a comment to the job

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        comment             Required string. Comment to add to job
        ===============     ====================================================================

        :return:
            Workflow Manager Comment Id

        """
        url = "{base}/jobs/{jobId}/comments".format(base=self._url, jobId=self.job_id)
        post_obj = {"comment": comment}

        return_obj = json.loads(
            self._gis._con.post(
                url,
                post_obj,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        return return_obj["commentId"]

    @property
    def comments(self):
        """
        Gets the comments of a job given job ID

        :return:
            `list <https://docs.python.org/3/library/stdtypes.html#list>`_ of comments

        """

        url = "{base}/jobs/{jobId}/comments?token={token}".format(
            base=self._url, jobId=self.job_id, token=self._gis._con.token
        )
        return_obj = self._gis._con.get(url)
        return return_obj["jobComments"]


class WMRole(object):
    """
    Represents a Workflow Manager Role object with accompanying GET, POST, and DELETE methods

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    init_data           data object representing relevant parameters for GET or POST calls
    ===============     ====================================================================
    """

    _camelCase_to_underscore = _camelCase_to_underscore
    _underscore_to_camelcase = _underscore_to_camelcase

    def __init__(self, init_data):
        self.privileges = self.roleName = self.description = None
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])

    def get(gis, url, params):
        role_dict = gis._con.get(url, params)
        return WMRole(role_dict)

    def post(self, gis, url):
        post_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        return_obj = json.loads(
            gis._con.post(
                url,
                post_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj


class JobTemplate(object):
    """
    Represents a Workflow Manager Job Template object with accompanying GET, POST, and DELETE methods

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    init_data           data object representing relevant parameters for GET or POST calls
    ===============     ====================================================================
    """

    _camelCase_to_underscore = _camelCase_to_underscore
    _underscore_to_camelcase = _underscore_to_camelcase

    def __init__(self, init_data, gis=None, url=None):
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])
        self._gis = gis
        self._url = url

    def __getattr__(self, item):
        possible_fields = [
            "default_assigned_to",
            "last_updated_by",
            "diagram_id",
            "extended_property_table_definitions",
            "description",
            "job_template_name",
            "job_template_id",
            "default_start_date",
            "default_priority_name",
            "last_updated_date",
            "job_start_date_type",
            "diagram_name",
            "default_job_duration",
            "default_due_date",
            "state",
            "category",
            "default_assigned_type",
            "default_description",
        ]
        gis = object.__getattribute__(self, "_gis")
        url = object.__getattribute__(self, "_url")
        id = object.__getattribute__(self, "job_template_id")
        full_object = gis._con.get(url, {"token": gis._con.token})
        try:
            setattr(self, _camelCase_to_underscore(item), full_object[item])
            return full_object[item]
        except KeyError:
            if item in possible_fields:
                setattr(self, _camelCase_to_underscore(item), None)
                return None
            else:
                raise KeyError(f'The attribute "{item}" is invalid for Job Templates')

    def get(gis, url, params):
        job_template_dict = gis._con.get(url, params)
        return JobTemplate(job_template_dict, gis, url)

    def put(self, gis, url):
        put_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        return_obj = json.loads(
            gis._con.put(
                url,
                put_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def post(self, gis, url):
        post_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        return_obj = json.loads(
            gis._con.post(
                url,
                post_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj["jobTemplateId"]

    def delete(gis, url):
        return_obj = json.loads(gis._con.delete(url, add_token=False, try_json=False))
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def share(self, group_ids):
        """
        Shares a job template with the list of groups

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        group_ids           Required list. List of Workflow Group Ids
        ===============     ====================================================================

        :return:
            boolean
        """
        try:
            url = "{base}/shareWith?token={token}".format(
                base=self._url,
                templateId=self.job_template_id,
                token=self._gis._con.token,
            )
            post_dict = {"groupIds": group_ids}

            return_obj = json.loads(
                self._gis._con.post(
                    url,
                    post_dict,
                    add_token=False,
                    post_json=True,
                    try_json=False,
                    json_encode=False,
                )
            )

            if "error" in return_obj:
                self._gis._con._handle_json_error(return_obj["error"], 0)
            elif "success" in return_obj:
                return return_obj["success"]
        except:
            self._handle_error(sys.exc_info())

    @property
    def share_details(self):
        """
        Returns the list of groups that the job_template is shared with by template_id.

        :return:
            list of :class:`~arcgis.gis.workflowmanager.Group` ID

        """

        url = "{base}/shareWith?token={token}".format(
            base=self._url, templateId=self.job_template_id, token=self._gis._con.token
        )
        return_obj = self._gis._con.get(url)

        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj["groupIds"]

    @property
    def automated_creations(self):
        """
        Retrieve the list of created automations for a job template, including scheduled job creation and webhook.

        :return:
            list of automatedCreations associated with the JobTemplate

        """
        try:
            return_obj = self._gis._con.get(
                "{base}/automatedCreation".format(
                    base=self._url, jobTemplateId=self.job_template_id
                ),
                params={"token": self._gis._con.token},
            )
            return return_obj["automations"]
        except:
            self._handle_error(sys.exc_info())

    def automated_creation(self, automation_id):
        """
        Returns the specified automated creation

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        automation_id       Required string. Automation Creation Id
        ===============     ====================================================================

        :return:
            automated creation object.

        """
        try:
            return_obj = self._gis._con.get(
                "{base}/automatedCreation/{automationId}".format(
                    base=self._url,
                    jobTemplateId=self.job_template_id,
                    automationId=automation_id,
                ),
                params={"token": self._gis._con.token},
            )
            return return_obj
        except:
            self._handle_error(sys.exc_info())

    def update_automated_creation(self, adds=None, updates=None, deletes=None):
        """
        Creates an automated creation

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        adds                Optional List. The list of automated creations to create.
        ---------------     --------------------------------------------------------------------
        updates             Optional List. The list of automated creations to update
        ---------------     --------------------------------------------------------------------
        deletes             Optional List. The list of automated creation ids to delete
        ===============     ====================================================================

        :return:
            success object

        .. code-block:: python

            # USAGE EXAMPLE: Creating a automated creation for a job template

            # create a WorkflowManager object from the workflow item
            wm = WorkflowManager(wf_item)

            # create the props object with the required automation properties
            adds = [{
                        "automationName": "auto_mation",
                        "automationType": "Scheduled",
                        "enabled": True,
                        "details": "{\"timeType\":\"NumberOfDays\",\"dayOfMonth\":1,\"hour\":8,\"minutes\":0}"
                    }]
            updates = [
                    {
                      "automationId": "abc123",
                      "automationName": "automation_updated"
                    }
                  ]
            deletes =  ["def456"]

            wm.update_automated_creation(adds, updates, deletes)
            >> True  # returns true if created successfully

        """
        if adds is None:
            adds = []
        if deletes is None:
            deletes = []
        if updates is None:
            updates = []

        props = {"adds": adds, "updates": updates, "deletes": deletes}
        url = "{base}/automatedCreation?token={token}".format(
            base=self._url,
            jobTemplateId=self.job_template_id,
            token=self._gis._con.token,
        )

        return_obj = json.loads(
            self._gis._con.post(
                url,
                props,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            self._gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return return_obj


class Group(object):
    """
    Represents a Workflow Manager Group object with accompanying GET, POST, and DELETE methods

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    init_data           data object representing relevant parameters for GET or POST calls
    ===============     ====================================================================
    """

    _camelCase_to_underscore = _camelCase_to_underscore

    def __init__(self, init_data):
        self.roles = None
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])

    def get(gis, url, params):
        group_dict = gis._con.get(url, params)
        return Group(group_dict)


class JobDiagram(object):
    """
    Helper class for managing Workflow Manager :class:`job diagrams <arcgis.gis.workflowmanager.JobDiagram>`
    in a workflow :class:`item <arcgis.gis.Item>`. This class is not created directly. An instance
    can be created by calling the :attr:`~arcgis.gis.workflowmanager.WorkflowManager.diagrams` property
    of the :class:`~arcgis.gis.workflowmanager.WorkflowManager` to retrieve a list of diagrams. Then
    the :meth:`~arcgis.gis.workflowmanager.WorkflowManager.diagram` method can be used with the appropriate
    ID of the digram to retrieve the :class:`job diagram <arcgis.gis.workflowmanager.JobDiagram>`.

    """

    _camelCase_to_underscore = _camelCase_to_underscore
    _underscore_to_camelcase = _underscore_to_camelcase

    def __init__(self, init_data, gis=None, url=None):
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])
        self._gis = gis
        self._url = url

    def __getattr__(self, item):
        possible_fields = [
            "display_grid",
            "diagram_version",
            "diagram_name",
            "diagram_id",
            "description",
            "annotations",
            "initial_step_id",
            "data_sources",
            "steps",
            "initial_step_name",
        ]
        gis = object.__getattribute__(self, "_gis")
        url = object.__getattribute__(self, "_url")
        id = object.__getattribute__(self, "diagram_id")
        full_object = gis._con.get(url, {"token": gis._con.token})
        try:
            setattr(self, _camelCase_to_underscore(item), full_object[item])
            return full_object[item]
        except KeyError:
            if item in possible_fields:
                setattr(self, _camelCase_to_underscore(item), None)
                return None
            else:
                raise KeyError(f'The attribute "{item}" is invalid for Diagrams')

    def get(gis, url, params):
        job_diagram_dict = gis._con.get(url, params)
        return JobDiagram(job_diagram_dict, gis, url)

    def post(self, gis, url):
        post_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        return_obj = json.loads(
            gis._con.post(
                url,
                post_dict,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def update(self, gis, url, delete_draft):
        clean_dict = {
            _underscore_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if v is not None
        }
        post_object = {"deleteDraft": delete_draft, "diagram": clean_dict}
        return_obj = json.loads(
            gis._con.post(
                url,
                post_object,
                add_token=False,
                post_json=True,
                try_json=False,
                json_encode=False,
            )
        )
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj

    def delete(gis, url):
        return_obj = json.loads(gis._con.delete(url, add_token=False, try_json=False))
        if "error" in return_obj:
            gis._con._handle_json_error(return_obj["error"], 0)
        elif "success" in return_obj:
            return return_obj["success"]
        return_obj = {
            _camelCase_to_underscore(k): v
            for k, v in return_obj.items()
            if v is not None and not k.startswith("_")
        }
        return return_obj


class JobLocation(object):
    """
    Represents a Workflow Manager Job Location object with accompanying GET, POST, and DELETE methods

    ===============     ====================================================================
    **Argument**        **Description**
    ---------------     --------------------------------------------------------------------
    init_data           Required object. Represents. relevant parameters for GET or POST calls
    ===============     ====================================================================
    """

    _camelCase_to_underscore = _camelCase_to_underscore

    def __init__(self, init_data):
        self.geometry = self.geometry_type = None
        for key in init_data:
            setattr(self, _camelCase_to_underscore(key), init_data[key])

    def get(gis, url, params):
        job_location_dict = gis._con.get(url, params)
        return JobLocation(job_location_dict)
