import { useNavigate, useParams } from "react-router-dom";
import Patient from "../../models/patient";
import { useEffect, useState } from "react";
import { getTherapistPatient } from "../../services/api-service";
import * as d3 from "d3";
import { Dropdown, IDropdownOption } from "@fluentui/react";
import { dashboardClassName, dateEmotionDivClassName, dropdownDivClassName, dropdownStyle, frequencyDivClassName, personalDetailsDivClassName, statisticsDivClassName, titleClassName } from "./patient-page-style";

export const PatientPage = () => {
    const navigate = useNavigate();
    const { id } = useParams();
    const [patient, setPatient] = useState<Patient>();
    const token = localStorage.getItem("token");
    const [selectedDate, setSelectedDate] = useState<string>();
    const [availableDates, setAvailableDates] = useState<IDropdownOption[]>([]);
    const [emotions, setEmotions] = useState<string[]>([]);

    useEffect(() => {
        if (token) {
            if (localStorage.getItem('userType') !== 'therapist') {
                if (localStorage.getItem('userType') === 'patient') {
                    navigate('/patient');
                } else {
                    navigate('/login');
                }
            }
        } else {
            navigate('/login');
        }
        const patient_id = parseInt(id!);
        getTherapistPatient(token!, patient_id).then((response) => {
            setPatient(response);
        }).catch((error) => {
            console.log(error);
            alert(error);
        });
    }, [token, id]);

    useEffect(() => {
        if (patient) {
            getAndSetAvailableDates();
            createEmotionsPieChart();
        }
    }, [patient]);

    const getAndSetAvailableDates = () => {
        if (patient) {
            const dates = patient.emotions.map((emotion) => emotion.date);
            // remove duplicates from dates
            const uniqueDates = dates.filter((date, index) => dates.indexOf(date) === index);
            const dropdownOptions = uniqueDates.map((date) => {
                const dateConv = new Date(date);
                const dateStr = dateConv.toLocaleDateString();
                return {key: dateStr,
                        text: dateStr};
            });
            setAvailableDates(dropdownOptions);
            console.log(dropdownOptions);
        }
    };

    const createEmotionsPieChart = () => {
        const emotionsCount = new Map<string, number>();
        patient?.emotions.forEach((emotion) => {
            if (emotionsCount.has(emotion.emotion)) {
                emotionsCount.set(emotion.emotion, emotionsCount.get(emotion.emotion)! + 1);
            } else {
                emotionsCount.set(emotion.emotion, 1);
            }
        });

        const pieData = Array.from(emotionsCount, ([emotion, count]) => (
            {emotion, count}
        ));

        const width: number = 300;
        const height: number = 300;
        const radius: number = Math.min(width, height) / 2;

        const svg = d3
            .select("#emotions-pie-chart")
            .selectAll("svg")
            .remove()
            .exit()
            .data([null])
            .enter()
            .append("svg")
            .attr("width", width)
            .attr("height", height + 50)
            ;

        const g = svg
            .append("g")
            .attr("transform", `translate(${width / 2}, ${(height + 50) / 2})`);

        const pie = d3.pie<{emotion: string; count: number}>().value((d: any) => d.count);
        const arc = d3.arc<d3.PieArcDatum<{emotion: string; count: number}>>().innerRadius(0).outerRadius(radius-10);
        const slices = g.selectAll("path").data(pie(pieData));

        slices
            .enter()
            .append("path")
            .attr("d", arc as any)
            .attr("fill", (d) => d3.schemeCategory10[d.index])
            .attr("stroke", "#fff")
            .style("stroke-width", "2px");

        const labels = g
            .selectAll("text")
            .data(pie(pieData));

        labels
            .enter()
            .append("text")
            .attr("transform", (d) => `translate(${arc.centroid(d)})`)
            .attr("dy", "0.35em")
            .style("text-anchor", "middle")
            .style("font-size", 12)
            .style("fill", "white")
            .text((d) => d.data.emotion);

        svg
        .append("text")
        .attr("x", width / 2)
        .attr("y", 20)
        .attr("text-anchor", "middle")
        .style("font-size", 16)
        .text("Emotions and their frequency");
    };

    const handleDateChange = (event: React.FormEvent<HTMLDivElement>, option?: IDropdownOption) => {
        if (option) {
            const date = option.key as string;
            setSelectedDate(date);
            // set emotions for that date
            const emotionsForDate = patient?.emotions.filter((emotion) => { 
                const emotionDate = new Date(emotion.date);
                return emotionDate.toLocaleDateString() === date});
            if (emotionsForDate) {
                const emotions = emotionsForDate.map((emotion) => emotion.emotion);
                // make the emotions unique
                const uniqueEmotions = emotions.filter((emotion, index) => emotions.indexOf(emotion) === index);
                setEmotions(uniqueEmotions);
            }
        }
    }

    return (
        <div className={dashboardClassName}>
            <h1 className={titleClassName}>{patient?.first_name} {patient?.last_name}'s dashboard</h1>
            <div className={personalDetailsDivClassName}>
                <p>First name: {patient?.first_name}</p>
                <p>Last name: {patient?.last_name}</p>
                <p>Email: {patient?.email}</p>
                <p>Date of birth: {patient?.date_of_birth.toLocaleDateString()}</p>
                <p>Gender: {patient?.gender}</p>
                <p>Country: {patient?.country}</p>
                <p>City: {patient?.city}</p>
            </div>
            <div className={statisticsDivClassName}>
                <div className={dateEmotionDivClassName}>
                    <p>Select a date: </p>
                    <Dropdown 
                        className={dropdownDivClassName}
                        options={availableDates}    
                        placeholder="--Select a date--"
                        onChange={handleDateChange}
                        selectedKey={selectedDate}
                        styles={dropdownStyle}
                    />
                    {selectedDate && (
                        <div>
                            <p>Emotions for {selectedDate}: </p>
                            {emotions.length > 0 
                            ? (
                                emotions.map((emotion, index) => (
                                    <p key={index}>{emotion}</p>
                                ))
                            )
                            : (
                                <p>No emotions recorded for this date.</p>
                            )}
                        </div>
                    )}
                </div>
                <div className={frequencyDivClassName}>
                    <p>Statistics: </p>
                    <div id="emotions-pie-chart">
                    </div>
                </div>
            </div>
            
        </div>
    );
}