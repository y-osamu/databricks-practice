# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %sql
# MAGIC -- Which artists released the most songs each year in 1990 or later?
# MAGIC SELECT artist_name, total_number_of_songs, year
# MAGIC   FROM workspace.sdp.top_artists_by_year
# MAGIC   WHERE year >= 1990
# MAGIC   ORDER BY total_number_of_songs DESC, year DESC;
