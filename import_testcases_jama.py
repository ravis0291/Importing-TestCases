#! /usr/bin/python
'''
Script to import V+V test cases into JAMA

Copyright Dynamic Controls 2016

Requires pyjama2
'''

import re
import time
import os
import unittest
import pyjama2 as jama

# Get the directory containing the .py files
path = os.path.dirname(os.path.realpath(__file__))
path = os.path.dirname(path)
path = os.path.join(path, "pyIntegrationTestFramework/integrationtest")

test_files = []

script_start_time = time.time()

for (dirpath, dirnames, filenames) in os.walk(path):
    # Add all the .py files that contain tests
    test_files.extend(os.path.join(dirpath, filename) for filename in filenames if filename.endswith(".py"))

# TODO - change the container
sandbox_id = 747909  # Document ID for Sandbox (currently Ravi's Sandbox)
sandbox = jama.Interface.get_item(sandbox_id)
# test_set = next(test_case_set for test_case_set in sandbox.get_children(item_type=jama.items.Set)
#                 if test_case_set.child_item_type_id == jama.items.SoftwareTestCase.TYPE_ID)

proj_id = 101  # Sandbox currently

################################################################################################################################
#############################  Functions for creating sub components under SW V+V testcases component  #########################
def create_sw_test_case_component():
    """
    Creates sub components similar to 'Specifications' component under the 'Software Test Cases' component
    Returns a set which holds test cases that don't have any requirement references
    """
    item = jama.Interface.get_item(key="UD_ARCH-CMP-3")  # This is the ID for 'Specifications' component in JAMA
    sub_components_1 = item.get_children(item_type=jama.items.Component)  # Get all the sub components in the 'Specifications' folder
    my_sandbox = jama.Interface.get_item(key="TEST-CMP-100")
    create_components_recursive(item, my_sandbox)
    miscellaneous_set = jama.Interface.search(name="Miscellaneous Software Test cases")[0]
    if not miscellaneous_set:
        # This is the container for tests that do not have any requirement references
        miscellaneous_set = jama.items.Set.create(my_sandbox, "Miscellaneous Software Test cases", jama.items.SoftwareTestCase, 'SW_TC')
    sw_risk_set = jama.Interface.search(name="Risk Analysis - Software Test Cases")[0]
    if not sw_risk_set:
        # This is the container for the requirements under Risk Analysis component which doesn't come under Specifications component
        sw_risk_set = jama.items.Set.create(my_sandbox, "Risk Analysis - Software Test Cases", jama.items.SoftwareTestCase, "SW_TC")
    not_specifications_set = jama.Interface.search(name="Test Cases not coming under Specifications component")[0]
    if not not_specifications_set:
        # This is the container for the requirements that do not come under the Specifications component
        not_specifications_set = jama.items.Set.create(my_sandbox, "Test Cases not coming under Specifications component", jama.items.SoftwareTestCase, "SW_TC")
    return miscellaneous_set, sw_risk_set, not_specifications_set

def create_components_recursive(spec_component, vv_component):
    """
    spec_component - Specifications component to look under
    vv_component - V+V component under which we should create the new component
    """
    sub_components = spec_component.get_children(item_type=jama.items.Component)  # Get all the sub components in the 'Specifications' folder
    if sub_components:
        for sub_component in sub_components:
            existing_sub_components = [child.name for child in vv_component.get_children(item_type=jama.items.Component)]
            # Check if the item already exists in JAMA
            if not sub_component.name in existing_sub_components:
                test_case_sub_component = jama.items.Component.create(vv_component, sub_component.name)
                jama.items.Set.create(test_case_sub_component, '{} - Software Test Cases'.format(sub_component.name), jama.items.SoftwareTestCase, 'SW_TC')
                print "Creating sub component - {}".format(sub_component.name)
                # Call the function recursively to create all sub components present in this sub component
                create_components_recursive(sub_component, test_case_sub_component)
            else:
                print "{} already exists in JAMA".format(sub_component.name)
################################################################################################################################
################################################################################################################################

def get_parent_component_for_requirement(requirement):
    """
    Gets the first parent component for a particular requirement.
    This function is useful for placing the test cases based on the requirement into the correct location
    """
    req_jama = jama.Interface.get_item(key=requirement)
    parent = jama.Interface.get_item(req_jama.parent_id)
    # Iterate until the parent item's type is a Component
    while not isinstance(parent, jama.items.Component):
        parent = jama.Interface.get_item(parent.parent_id)
    temp_holder = parent
    parents_list_original = []
    while parent.has_parent:
        parents_list_original.append(parent.name)
        parent = jama.Interface.get_item(parent.parent_id)
    parent = temp_holder
    # Search through JAMA to get the correct component i.e. the one which is not under the 'Specifications' component but in
    # the replicate new component that we created to place the software test cases
    results = jama.Interface.search(name=parent.name, item_type=jama.items.Component)
    #print results,"before filter"
    #print [result.project_id for result in results], "project ids of results"
    #print parent.name,"parent component name", req_jama,"req"
    #results = [result for result in results if result.project_id == proj_id]
    req_testcase_component = None
    valid_specs = False
    print results,"--------> results"
    for result in results:
        #print result,"before filters"
        if result.project_id == proj_id:
            #print result,"in sandbox"
            try:
                parent_res = jama.Interface.get_item(result.parent_id)
            except KeyError:
                print result.id
            parents_list = []
            # Iterate until you get to an item which doesn't have a parent i.e. until you get to the top most component
            while parent_res.has_parent:
                parents_list.append(parent_res.name)
                parent_res = jama.Interface.get_item(parent_res.parent_id)
            print "\n\n",parents_list_original[1:], parents_list,"\n\n"
            # NOTE: Change id while running in the actual project
            # Check if the parent component is not the 'Specifications' component
            if parent_res.id != 11108 and parents_list == parents_list_original[1:] and parent_res.id == 747909:
                req_testcase_component = result
                valid_specs = True
                break
                #print '********',result
            else:
                pass
                #print result,"#######"
        elif result.project_id == 41 and result.id == 338924:
            #print result,"risk analysis"
            return sw_risk_set
        else:
            print "-------------------------------------------------------"
            print "!!!Spec doesn't come under Specifications component!!!!"
    if not valid_specs: return not_specifications_set
    #print req_testcase_component
    # Each sub component in 'SW test cases' contains a set to hold software test cases
    child_sets = req_testcase_component.get_children(jama.items.Set)
    return child_sets[0]

def parse_file(filename):
    '''
    Iterates through the file contents and obtains tests and their corresponding docstrings
    '''
    test_list = {}
    references = {}
    with open(filename, 'r') as f:
        lines = f.readlines()
        text = "".join(lines)
    test_names = re.findall(r'def (test_.*?)\(', text)

    # Go through each file to obtain the requirements and docstrings
    for name in test_names:
        docstring = re.search(r"'''(.*?)'''", text[text.find(name):], re.DOTALL)
        test_list[name] = docstring.group(1)
        references[name] = set(re.findall(r'\[(.*?)\]', docstring.group(1)))
    return test_list, references

def parse_docstring(docstring):
    '''
    Analyses given docstring and adds formatting such as
1) Removing sections that are empty
2) Moving the 'NOTES' section to 'Notes' column in test step
3) Adding line breaks to each line to improve appearance in JAMA
    '''
    notes_string = ""
    #########################################################################
    # Remove empty sections and retrieve string in 'NOTES' section if present
    #########################################################################
    if re.findall(r'NOTES\s*ANOMALIES\s*$', docstring):  # 'NOTES' and 'ANOMALIES' sections are empty
        docstring = re.sub(r'NOTES\s*ANOMALIES\s*', '', docstring)

    elif re.findall(r'NOTES[\s\S]*ANOMALIES\s*$', docstring):  # 'ANOMALIES' section is empty
        docstring = re.sub(r'ANOMALIES\s*$', '', docstring)
        notes_string = re.search(r'(NOTES\s((\s*\S+)+))', docstring, flags=re.M)
        docstring = re.sub(re.escape(notes_string.group(1)), '', docstring)
        notes_string = notes_string.group(2)

    elif re.findall(r'NOTES(\s*)ANOMALIES(\s*\S+\s*)', docstring):  # 'NOTES' section is empty
        docstring = re.sub(r'NOTES(\s*)', '', docstring)

    else:  # 'NOTES' and 'ANOMALIES' sections are present
        notes_string = re.search(r'(NOTES(.*?))ANOMALIES', docstring, flags=re.DOTALL)
        docstring = re.sub(re.escape(notes_string.group(1)), '', docstring)
        notes_string = notes_string.group(2)

    ################################
    # Add line breaks and formatting
    ################################
    docstring = re.sub(r'((WHEN|THEN|NOTES|ANOMALIES)(\s?\S*))',
                       r'<br><br><b>\g<1></b><br>', docstring)  # 'WHEN', 'THEN', 'NOTES', 'ANOMALIES' sections

    docstring = re.sub(r'((GIVEN)(\s?\S*))',
                       r'<br><b>\g<1></b><br>', docstring)  # 'GIVEN' section

    # Old style 'Then's
    docstring = re.sub(r'((Then)[2-9](:)+)', r'<br><br>\g<1>', docstring)

    docstring = re.sub(r'((Then)[1-9](:)+)', r'<i>\g<1></i>', docstring)

    return docstring, notes_string

def create_links(docstring):
    '''
    Gets the references in the docstring and makes them hyperlinks
    '''
    matches = re.findall(r'\[([A-Z\-_0-9]+?)\]+?', docstring)  # Regex to match all references
    unique_matches = set(matches)

    for match in unique_matches:
        try:  # Add hyperlink only when there is a valid reference
            jama_link = jama.Interface.get_item(key=match).url

            if jama_link:
                docstring = re.sub(re.escape(match), '<a href="{0}">{1}</a>'.format(jama_link, match), docstring)
        except: pass

    return docstring

##################################################################################################################
#######################################  Functions used for Test Runs  ###########################################
def get_napi_vectors(requirements):
    '''
    Returns the list of NAPI vectors that the requirement is linked to.
    '''
    vectors_to_run = []
    for requirement in requirements:
        requirement = jama.Interface.get_item(key=requirement)
        abbs = requirement.get_downstream_items(item_type=jama.items.ApplicationBuildingBlock)

        for abb in abbs:
            napi_versions = abb.get_upstream_items(item_type=jama.items.Napi)

            for napi_version in napi_versions:
                napi_vectors = napi_version.get_downstream_items(jama.items.NapiVector)
                vectors_to_run += napi_vectors
        print "Requirement: {}".format(requirement)
        print "Vectors supported: {}".format(vectors_to_run)
    return vectors_to_run

def get_requirements_for_product_configuration(prod_config_id):
    '''
    Get the requirements that are applicable for a particular product configuration
    '''
    reqs = []

    prod_config = jama.Interface.get_item(id=738339)  # Currently UD_ARCH-UD_PRD_CFG-120

    # 1 to 1 mapping between Software release and Product Configuration
    sw_release = prod_config.get_upstream_item(item_type=jama.items.SoftwareRelease)

    # 1 to many mapping between Software Release and Application Versions
    app_versions = sw_release.get_upstream_items(item_type=jama.items.ApplicationVersion)

    for app_version in app_versions:
        # 1 to 1 mapping
        print "\nLooking in {} \n".format(app_version.name)
        #if app_version.name == "AL PM MR3.0 RC4 Application": continue
        try:
            napi_vector = app_version.get_upstream_item(item_type=jama.items.NapiVector)
        except:
            print "\nSkipping App Version since it doesn't have any NAPI Vectors\n"
            continue
        napis = napi_vector.get_upstream_items(item_type=jama.items.Napi)

        for napi in napis:
            print "\n\tLooking further into {} \n".format(napi.name)
            abbs = napi.get_downstream_items(item_type=jama.items.ApplicationBuildingBlock)
            for abb in abbs:
                print "\n\t\tLooking deep further into {} \n".format(abb.name)
                temp = abb.get_upstream_items(item_type=jama.items.SystemRequirement)
                reqs += temp
                #for t in temp:
                #    print t.name + "(" + t.key + ")"
                print "\t\t{}".format(len(temp))

    print reqs
    print len(reqs)
#################################################################################################################
#################################################################################################################

def get_requirements_from_references(references):
    '''
    Returns requirements from the set of references in the docstring of a test
    '''
    requirements = []
    for item in references:
        try:
            item_type = jama.Interface.get_item(key=item)
            if item_type.type_id == jama.items.SystemRequirement.TYPE_ID:
                requirements.append(item)
#             else:
#                 print "{} is not a requirement".format(item)
        except Exception as e:
            print "\n{} not found and exception is {}\n".format(item, e)
    return requirements

def create_relationships(requirements, item):
    '''
    Create relationships between a software test case and its corresponding requirement(s)
    '''
    item_type = ""

    for requirement in requirements:  # Iterate through the requirements in the test and add relationship
        if jama.Interface.search(key=requirement):  # Check if the item exists in JAMA
            req = jama.Interface.search(key=requirement)
            downstream_items = req[0].get_downstream_items()
            downstream_items_names = [downstream_items[x].name for x in range(len(downstream_items))]

            if not item.name in downstream_items_names:
                rel = jama.relationships.Tests.create(item, req[0])
                print "Added relationship between '{}' and '{}'".format(item.name, req[0].name)
            else:
                print "A relationship already exists between {} and {}".format(item.name, req[0].name)
        else:
            print "No such item '{}' in JAMA".format(requirement)

def get_requirements_in_specifications_component(test_requirements):
    requirements_specications_component = []
    for req in test_requirements:
        pass


#existing_test_cases = test_set.get_children()  # Obtain the existing software test cases
#test_case_names = [existing_test_cases[x].name for x in range(len(existing_test_cases))]

############### This code is to create the components and sets required ##############
miscellaneous_set, sw_risk_set, not_specifications_set = create_sw_test_case_component()
######################################################################################

test_count = 0
file_count = 0

#current_set = jama.Interface.get_item(id=749783)

# Iterate through each python file that has tests in it
for test_file in test_files:
    print "Scanned {} files".format(file_count)
    file_count += 1

    # Get the list of test names and references present in the file
    test_list, references =  parse_file(test_file)
    print "----Scanning file: {}----".format(test_file)

    if file_count <= 36:
        continue

    # Iterate through each test in the file
    for test in test_list:
        test_count += 1
        test_start_time = time.time()  # Get the current time

        if test_count <= 769:
            continue

        # Replaces the references text to links
        test_list[test] = create_links(test_list[test])
        print "{}) Scanning test: {}".format(test_count, test)

        # Updates the docstring to make it appear good in test case item
        new_docstring, notes_string = parse_docstring(test_list[test])

        # Gets the list of valid requirements present in the test
        test_requirements = get_requirements_from_references(references[test])

        # Get the correct 'set' item under which the test case relating to the requirement should be placed
        # If there are not any valid requirement references, place them in the miscellaneous set
        interested_set = get_parent_component_for_requirement(test_requirements[0]) if test_requirements else miscellaneous_set

        if len(test_requirements) == 0:
            print "\t'{}' does not have any requirements relationships".format(test)

        # if test not in test_case_names:  # Check if the test to be added is present already in JAMA
        if not jama.Interface.search(name=test):  # Check if the test to be added is present already in JAMA
            print interested_set, "Interested Set"
            item = jama.items.SoftwareTestCase.create(interested_set, test)

            if not notes_string:  # Add test steps based on whether there is a 'NOTES' section in docstring
                item.test_steps = [jama.items.SoftwareTestCase.TestStep(new_docstring, 'PASS')]
            else:
                item.test_steps = [jama.items.SoftwareTestCase.TestStep(new_docstring,
                                                                         'PASS', notes_string)]

#             # Add relationships only if there are any valid requirement references in the test 
#             if test_requirements:
#                 create_relationships(test_requirements, item)
#                 get_napi_vectors(test_requirements)

            item.commit()  # Commit the changes before adding another test case
            try:
                print "Requirement:",test_requirements[0]
            except Exception:
                pass
            print "--Added {} testcase to JAMA in {} seconds--".format(test, time.time() - test_start_time)
        else:
            print "{} already exists in JAMA".format(test)
        #break  # TODO - remove once finalized
#    break  # TODO - remove once finalized

print "--Added {} testcase(s) to JAMA in {} seconds--".format(test_count, time.time() - script_start_time)