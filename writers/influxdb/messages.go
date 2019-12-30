// Copyright (c) Mainflux
// SPDX-License-Identifier: Apache-2.0

package influxdb

import (
	"fmt"
	"math"
	"strconv"
	"time"

	influxdata "github.com/influxdata/influxdb/client/v2"
	"github.com/mainflux/mainflux/transformers/senml"
	"github.com/mainflux/mainflux/writers"
)

const pointName = "messages"

var (
	_            writers.MessageRepository = (*influxRepo)(nil)
	InfluxDBName string
	clients      influxdata.Client
	channel      string
	q_channel    string
	quote        string
	final_error  error
)

type influxRepo struct {
	client influxdata.Client
	cfg    influxdata.BatchPointsConfig
}

type fields map[string]interface{}
type tags map[string]string

// This is utility function to query the database.
func queryDB(cmd string) ([][]interface{}, error) {
	q := influxdata.Query{
		Command:  cmd,
		Database: InfluxDBName,
	}
	response, err := clients.Query(q)
	if err != nil {
		return nil, err
	}
	if response.Error() != nil {
		return nil, response.Error()
	}
	if len(response.Results[0].Series) == 0 {
		return nil, nil
	}
	// There is only one query, so only one result and
	// all data are stored in the same series.
	return response.Results[0].Series[0].Values, nil
}

// New returns new InfluxDB writer.
func New(client influxdata.Client, database string) writers.MessageRepository {
	clients = client
	return &influxRepo{
		client: client,
		cfg: influxdata.BatchPointsConfig{
			Database: database,
		},
	}
}

func (repo *influxRepo) Save(messages ...senml.Message) error {
	for _, msg := range messages {
		tgs, flds := repo.tagsOf(&msg), repo.fieldsOf(&msg)
		InfluxDBName = channel
		_, err := queryDB(fmt.Sprintf("CREATE DATABASE %s", q_channel))
		fmt.Println(err)
		bp, err := influxdata.NewBatchPoints(influxdata.BatchPointsConfig{
			Database: InfluxDBName})
		if err != nil {
			return err
		}

		sec, dec := math.Modf(msg.Time)
		t := time.Unix(int64(sec), int64(dec*(1e9)))

		pt, err := influxdata.NewPoint(pointName, tgs, flds, t)
		if err != nil {
			return err
		}
		bp.AddPoint(pt)
		final_error = repo.client.Write(bp)
	}
	return final_error
}

func (repo *influxRepo) tagsOf(msg *senml.Message) tags {
	quote = "\""
	q_channel = quote + msg.Channel + quote
	channel = msg.Channel
	return tags{
		"channel":   msg.Channel,
		"subtopic":  msg.Subtopic,
		"publisher": msg.Publisher,
		"name":      msg.Name,
	}
}

func (repo *influxRepo) fieldsOf(msg *senml.Message) fields {
	updateTime := strconv.FormatFloat(msg.UpdateTime, 'f', -1, 64)
	ret := fields{
		"protocol":   msg.Protocol,
		"unit":       msg.Unit,
		"updateTime": updateTime,
	}

	switch {
	case msg.Value != nil:
		ret["value"] = *msg.Value
	case msg.StringValue != nil:
		ret["stringValue"] = *msg.StringValue
	case msg.DataValue != nil:
		ret["dataValue"] = *msg.DataValue
	case msg.BoolValue != nil:
		ret["boolValue"] = *msg.BoolValue
	}

	if msg.Sum != nil {
		ret["sum"] = *msg.Sum
	}

	return ret
}
