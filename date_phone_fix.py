from os import remove
import streamlit as st
import numpy as np
import pandas as pd
import datetime
import xlrd
from collections import Counter
import random

def main():

    ### Config lookup 
    # config_lookup = {
    #     "saas": {
    #         "fields": ["first_name","last_name","patient_id","email","mobile","dob","gender","ethnicity","clinician_name","track_name","track_date"],
    #         "required_fields": ["first_name","patient_id","email","mobile"],
    #         "date_fields": ["dob","track_date"],
    #         "phone_fields": ["mobile"],
    #         "enum_fields": {
    #             "gender": ["Male", "Female"],
    #             "ethnicity": ["Sikh", "German", "New Zealand", "Australian", "Chinese", "Maori","Japanese", "English", "Irish", "Scottish", "Italian"]
    #         },
    #     },
    # }
   
    country_code_lookup = {
        "sg": {"code": "65", "digits_ex": 8 },
        "nz": {"code": "64", "digits_ex": 8 },
        "au": {"code": "61", "digits_ex": 8 }
    }

    # widget_key = random.randint(1, 10000000000000000)

################## Functions ########################
 ### functions
    def fix_excel_date(serial_date):
        """fix excel date with python datetime"""
        serial_int = int(serial_date) - 1
        return datetime.datetime(1899, 12, 31) + datetime.timedelta(days=serial_int)
        
    def process_input_df(df_input):
        """Data preprocessing for dataframe to get uploadable csv"""
        df = df_input.copy()

        ### Process date fields
        for date_field in date_fields:
            # print(f"date_field {df[date_field].dtype}")
            date_list = df[date_field].to_list()

            ### Fix Excel Fields
            new_list = []
            for item in date_list:
                # print(type(item))
                if item and len(str(item)) == 5:
                    new_list.append(fix_excel_date(item))
                else:
                    new_list.append(item)
            
            df[date_field] = new_list

            ### Convert to ISO-8601 format
            df[date_field] = pd.to_datetime(df[date_field])
            df[date_field] = df[date_field].dt.strftime('%Y-%m-%d')

        ### Initiate issues field
        df['upload_issues'] = ''

        ### Process phone number fields
        for phone_field in phone_fields:
            ### strip non numbers
            df[phone_field] = np.where((df[phone_field].str.match("^\+.*")) & (df[phone_field].notnull()), df[phone_field], df[phone_field].str.replace(r"[\D]",'', regex=True))
            
            ### name check fields
            check_field = phone_field + "_check"

            ### address those starting with "+", mark as clean
            df.loc[(df[phone_field].str.startswith("+")) & (df[phone_field].notnull()), check_field] = "clean"
            
            ### ignore everything starting with local country code, just add "+"
            df.loc[(df[phone_field].str.startswith(country_config['code'])) & (df[phone_field].notnull()), check_field] = "clean"
            df.loc[(df[phone_field].str.startswith(country_config['code'])) & (df[phone_field].notnull()), phone_field] = "+" + df[phone_field].astype(str)


            ### for items starting with 0, remove zero, then add +countrycode
            df.loc[(df[phone_field].str.startswith("0")) & (df[phone_field].notnull()), check_field] = "ambiguous"
            df.loc[(df[phone_field].str.startswith("0")) & (df[phone_field].notnull()), phone_field] = "+" + country_config['code']  + df[phone_field].str.lstrip("0")


            ### for items with same or less than optimal format, add local country code
            df.loc[(df[phone_field].astype(str).map(len) <= country_config['digits_ex']) & (df[phone_field].notnull()) , check_field] = "ambiguous"
            df.loc[(df[phone_field].astype(str).map(len) <= country_config['digits_ex']) & (df[phone_field].notnull()) , phone_field] = "+" + country_config['code']  + df[phone_field].astype(str)

            ### Highlight issues for malformed phone number
            df.loc[(df[check_field].isin(['ambiguous']) | df[check_field].isnull()), 'upload_issues' ] = df['upload_issues'].astype(str) + f", check {phone_field} field"
        

        # clean up upload_issues
        df['upload_issues'] = df['upload_issues'].str.lstrip(', ')

        # print(df.dtypes, "before return")
        return(df)


    def output_csv(dataframe, has_header=True): 
        """Takes a dataframe and has header argument to produce csv file to buffer for download button to use"""
        return dataframe.to_csv(sep=",", index=False, header=has_header).encode('utf-8')

    def download_success():
        """Success message on download"""
        st.success("Download Successful!")
        st.empty()
    
    ########################################### App ####################################
    ### Title
    st.title("Phone + Date Field Cleaner")

    ### Section 1: Upload source file
    st.header("Step 1: Upload File")
    input_file = st.file_uploader("Upload excel file here", type=['xls','xlsx','csv'], key='key_')

    if input_file is not None:
        if input_file.name.endswith('.csv'):
            input_df = pd.read_csv(input_file)
        else:
            input_df = pd.read_excel(input_file, dtype=str, parse_dates=False)
        
        col_list = input_df.columns
    
        ### Section 2: preferences
        with st.container() as container_1:
            st.header("Step 2: Select Options")
            with st.form(key='preferences'):
                output_name = st.text_input(label='Output file name')
                active_country = st.selectbox("Select country", country_code_lookup.keys(), 0)
                date_field_list = st.multiselect('Date Fields', col_list)
                phone_field_list = st.multiselect('Phone Fields', col_list)
                submit_button = st.form_submit_button(label='Confirm')
    
            ### set active country settings
            country_config = country_code_lookup[active_country]
            date_fields = date_field_list
            phone_fields = phone_field_list

            ### Checking if file is valid
            if submit_button:
                try:
                    st.success(f"{input_file.name} has been selected\n\n")
                    st.text("")
                    st.markdown("***")
                    st.header("\n\nStep 2: Check Data")
                    if input_file is None:
                        pass
                    elif input_file.name.endswith('.csv'):
                        input_df = pd.read_csv(input_file)
                    else:
                        input_df = pd.read_excel(input_file, dtype=str, parse_dates=False)
                    
            ### Display input_df
                    with st.container():
                        st.subheader("Input Data")
                        input_df

            ### Preprocess data
                    output_df = process_input_df(input_df)
                    # print(processed_df.dtypes, "processed")

            ### OUTPUT df container
                    container_output = st.container()
                    container_output.text("")
                    container_output.subheader("Output Data")
                    container_output.write(output_df)
                
                    
            ### Highlight: All issues
                    st.text("")
                    st.subheader("Frequency of issues")
                    issue_list = output_df['upload_issues'].str.cat(sep=', ').split(', ')
                    issue_dict = Counter(issue_list)
                    

                    for k,v in issue_dict.items():
                        print (k)
                        if k == "":
                            st.markdown("- **" + str(v) + " records with no issues**")
                        else:
                            st.markdown("- **" + k + ":** " + str(v) + " times")


            ### [Missing] Output of csv files    
                    if output_df is not None:

                        clean_df = output_df[col_list]

                        out_csv = output_csv(output_df, True)
                        out_csv_noheader = output_csv(clean_df, False)

                        csv_path = output_name + ".csv"
                        csv_path_noheader = output_name + "_for_upload.csv"
                        
                        st.text("")
                        st.markdown("***")
                        st.header("\n\nStep 4: Download CSV")
                        st.subheader("CSV with headers - for checking and fixing")
                        st.download_button(
                            label = "Download CSV (with headers)",
                            data=out_csv,
                            file_name=csv_path,
                            mime='text/csv',
                            on_click=download_success)



                        ### Don't allow download if there are issues
                        
                        st.text("")
                        st.text("")
                        
                        st.subheader("CSV without headers - to upload once data is clean")
                        # if missing_df[missing_df['required'] == 'Required'].shape[0] > 0 or count_missing > 0 :
                        #     st.warning("Required fields have issues. File is not ready for upload until they are fixed")

                        st.download_button(
                            label = "Download CSV (no headers)",
                            data = out_csv_noheader,
                            file_name = csv_path_noheader,
                            mime='text/csv', 
                            on_click=download_success)
            
    
                except AttributeError:
                    st.error("Please select a file before continuing")


if __name__ == '__main__':
    main()